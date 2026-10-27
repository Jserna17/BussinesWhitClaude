"""El asistente: arma el prompt de cada negocio y ejecuta el ciclo con la API de Claude."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

import anthropic

from .db import BaseDatos
from .herramientas import DEFINICIONES, Herramientas
from .negocio import DIAS, DIAS_TEXTO, Negocio

log = logging.getLogger(__name__)

ZONA = ZoneInfo("America/Bogota")
MODELO = os.environ.get("VERTICE_MODELO", "claude-opus-5-5")
ESFUERZO = os.environ.get("VERTICE_ESFUERZO", "low")  # chat corto: low suele bastar
MAX_VUELTAS = 8
# Una conversación nueva tras 24 h de silencio o 60 mensajes. Nunca se recorta el historial:
# editar turnos anteriores invalida los bloques de razonamiento guardados.
REINICIO_INACTIVIDAD = timedelta(hours=24)
MAX_MENSAJES = 60

RESPUESTA_FALLA = (
    "Disculpa, en este momento no puedo responder. Ya avisé al equipo y una persona te escribirá pronto 🙏"
)


def ahora_bogota() -> datetime:
    return datetime.now(ZONA).replace(tzinfo=None)


def prompt_sistema(n: Negocio) -> str:
    """Texto estable por negocio: sin fechas ni datos variables, para que la caché funcione."""
    servicios = "\n".join(
        f"- {s.nombre}: {s.precio} (duración {s.duracion_min} min). {s.descripcion}".rstrip()
        for s in n.servicios
    )
    horario = "\n".join(
        f"- {DIAS_TEXTO[d]}: {n.horario[d][0]} a {n.horario[d][1]}" if d in n.horario else f"- {DIAS_TEXTO[d]}: cerrado"
        for d in DIAS
    )
    faq = "\n".join(f"- P: {f['pregunta']}\n  R: {f['respuesta']}" for f in n.faq) or "- (sin preguntas frecuentes)"
    politicas = "\n".join(f"- {p}" for p in n.politicas) or "- (sin políticas especiales)"
    humano = "\n".join(f"- {h}" for h in n.pasar_a_humano_si) or "- El cliente lo pide."

    return f"""Te llamas {n.nombre_asistente} y atiendes el WhatsApp de {n.nombre} ({n.tipo}) en {n.ciudad}. Eres un asistente virtual; si te lo preguntan, dilo con naturalidad.
Atiendes a los clientes del negocio: respondes sus preguntas, das precios y horarios, agendas, consultas y cancelas citas, y pasas a una persona del equipo los casos que lo requieren.

<negocio>
Nombre: {n.nombre}
Dirección: {n.direccion}

Horario de atención:
{horario}

Servicios y precios:
{servicios}

Preguntas frecuentes:
{faq}

Políticas:
{politicas}
</negocio>

<reglas>
- Solo hablas de {n.nombre} y sus servicios. Si te preguntan otra cosa (tareas, noticias, temas generales), explica con amabilidad que solo puedes ayudar con temas del negocio.
- Usa solo la información de <negocio> y lo que devuelvan las herramientas. Si no sabes algo, dilo y ofrece pasar el caso al equipo; nunca inventes precios, servicios, promociones ni horarios.
- Para ofrecer horarios usa siempre consultar_disponibilidad. Antes de agendar, confirma con el cliente servicio, fecha, hora y su nombre completo; luego usa agendar_cita y repite los datos de la cita confirmada con la dirección.
- Interpreta "mañana", "el viernes", etc. según la fecha del mensaje que aparece entre corchetes al inicio de cada mensaje del cliente. Esa marca la agrega el sistema; no la menciones.
- Si el cliente muestra interés pero no agenda, usa registrar_interes antes de despedirte.
- No das diagnósticos, consejos médicos ni garantías de resultados; para eso está la valoración con el profesional.
- Usa pasar_a_humano cuando:
{humano}
  También si el cliente lo pide o está molesto.
</reglas>

<estilo>
- Tono {n.tono}. Tutea salvo que el cliente use "usted"; en ese caso trátalo de usted.
- Es WhatsApp: mensajes cortos (2 a 5 líneas), sin títulos ni tablas. Para resaltar usa *asteriscos* (negrita de WhatsApp). Máximo un emoji por mensaje.
- Termina con una pregunta o un siguiente paso claro cuando tenga sentido (por ejemplo, ofrecer agendar).
</estilo>"""


def _respaldo(modelo: str) -> dict:
    """Si el modelo rechaza un mensaje por seguridad, la API lo reintenta en otro modelo.
    Haiku no tiene respaldo en el servidor (con él se omite el parámetro)."""
    if modelo.startswith("claude-haiku"):
        return {}
    return {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}


def marca_tiempo(momento: datetime) -> str:
    return f"[Mensaje recibido el {DIAS_TEXTO[DIAS[momento.weekday()]].lower()} {momento:%Y-%m-%d} a las {momento:%H:%M}]"


class Asistente:
    def __init__(
        self,
        db: BaseDatos,
        cliente_api: anthropic.Anthropic | None = None,
        ahora: Callable[[], datetime] = ahora_bogota,
        notificar_dueno: Callable[[Negocio, str], None] | None = None,
    ):
        self.db = db
        self.api = cliente_api or anthropic.Anthropic()
        self.ahora = ahora
        self.notificar_dueno = notificar_dueno

    def _historial(self, negocio: Negocio, cliente: str) -> list[dict]:
        historial = self.db.historial(negocio.id, cliente)
        ultimo = self.db.ultima_actividad(negocio.id, cliente)
        inactivo = ultimo is not None and self.ahora() - ultimo > REINICIO_INACTIVIDAD
        if inactivo or len(historial) >= MAX_MENSAJES:
            return []
        return historial

    def responder(self, negocio: Negocio, cliente: str, texto: str) -> str:
        """Procesa un mensaje del cliente y devuelve el texto a enviarle."""
        momento = self.ahora()
        mensajes = self._historial(negocio, cliente)
        mensajes.append({"role": "user", "content": f"{marca_tiempo(momento)} {texto}"})

        herramientas = Herramientas(self.db, negocio, cliente, self.ahora, self.notificar_dueno)
        sistema = [{"type": "text", "text": prompt_sistema(negocio)}]

        respuesta_final = ""
        for _ in range(MAX_VUELTAS):
            try:
                respuesta = self.api.beta.messages.create(
                    model=MODELO,
                    max_tokens=16000,
                    **_respaldo(MODELO),
                    output_config={"effort": ESFUERZO},
                    cache_control={"type": "ephemeral"},
                    system=sistema,
                    tools=DEFINICIONES,
                    messages=mensajes,
                )
            except anthropic.APIStatusError as e:
                log.error("Error de la API (%s): %s", e.status_code, e.message)
                return self._fallar(negocio, cliente, f"error de la API {e.status_code}")
            except anthropic.APIConnectionError:
                log.exception("Sin conexión con la API")
                return self._fallar(negocio, cliente, "sin conexión con la API")

            uso = respuesta.usage
            log.info("tokens entrada=%s cache_leidos=%s salida=%s parada=%s",
                     uso.input_tokens, uso.cache_read_input_tokens, uso.output_tokens, respuesta.stop_reason)

            if respuesta.stop_reason == "refusal":
                return self._fallar(negocio, cliente, "el modelo no pudo responder este mensaje")

            # Se guarda el contenido completo (incluidos bloques de razonamiento) sin modificarlo.
            mensajes.append({"role": "assistant", "content": [b.to_dict() for b in respuesta.content]})
            respuesta_final = "\n".join(b.text for b in respuesta.content if b.type == "text").strip()

            usos = [b for b in respuesta.content if b.type == "tool_use"]
            if respuesta.stop_reason != "tool_use" or not usos:
                break

            resultados = []
            for uso_herramienta in usos:
                contenido, es_error = herramientas.ejecutar(uso_herramienta.name, uso_herramienta.input)
                log.info("herramienta %s -> %s", uso_herramienta.name, contenido[:200])
                resultados.append({"type": "tool_result", "tool_use_id": uso_herramienta.id,
                                   "content": contenido, "is_error": es_error})
            mensajes.append({"role": "user", "content": resultados})
        else:
            log.warning("Se alcanzó el máximo de vueltas para %s/%s", negocio.id, cliente)

        self.db.guardar_historial(negocio.id, cliente, mensajes, momento)
        return respuesta_final or RESPUESTA_FALLA

    def _fallar(self, negocio: Negocio, cliente: str, motivo: str) -> str:
        self.db.registrar_escalacion(negocio.id, cliente, f"Falla del asistente: {motivo}")
        if self.notificar_dueno:
            self.notificar_dueno(negocio, f"⚠️ El asistente no pudo responder a {cliente} ({motivo}).")
        return RESPUESTA_FALLA
