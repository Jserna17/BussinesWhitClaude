"""El asistente: arma el prompt de cada negocio y delega cada turno en el motor de IA elegido."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from .db import BaseDatos
from .herramientas import Herramientas
from .motores import FallaModelo, crear_motor
from .negocio import DIAS, DIAS_TEXTO, Negocio, texto_franjas

log = logging.getLogger(__name__)

ZONA = ZoneInfo("America/Bogota")
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
        f"- {s.nombre}: {s.precio} (duración {s.duracion_min} min). {s.descripcion}"
        f"{' Requiere valoración previa.' if s.requiere_valoracion else ''}".rstrip()
        for s in n.servicios
    )
    horario = "\n".join(f"- {DIAS_TEXTO[d]}: {texto_franjas(n.franjas(d))}" for d in DIAS)
    horario += ("\n- Festivos de Colombia: abierto con el horario de ese día." if n.abre_festivos
                else "\n- Festivos de Colombia: cerrado.")
    con_horario = [p for p in n.profesionales if "horario" in p]
    if con_horario:
        horario += "\n\nDías de atención de cada profesional:\n" + "\n".join(
            f"- {p['nombre']}: " + ", ".join(f"{DIAS_TEXTO[d].lower()} {texto_franjas(n.franjas_de(p['nombre'], d))}"
                                            for d in DIAS if n.franjas_de(p["nombre"], d))
            for p in con_horario)
    faq = "\n".join(f"- P: {f['pregunta']}\n  R: {f['respuesta']}" for f in n.faq) or "- (sin preguntas frecuentes)"
    politicas = "\n".join(f"- {p}" for p in n.politicas) or "- (sin políticas especiales)"
    humano = "\n".join(f"- {h}" for h in n.pasar_a_humano_si) or "- El cliente lo pide."
    recordatorios = (
        "- El sistema envía solo un recordatorio por WhatsApp antes de cada cita (el día anterior y unas horas antes); puedes decírselo al cliente. "
        "Si el cliente confirma que asistirá, usa confirmar_asistencia. Si pide cambiar la fecha, usa reprogramar_cita."
        if n.recordatorios and n.whatsapp_phone_number_id else
        "- No prometas recordatorios automáticos: este negocio no los tiene activos.")

    return f"""Te llamas {n.nombre_asistente} y atiendes el WhatsApp de {n.nombre} ({n.tipo}) en {n.ciudad}. Eres un asistente virtual; si te lo preguntan, dilo con naturalidad.
Atiendes a los clientes del negocio: respondes sus preguntas, das precios y horarios, agendas, consultas, reprogramas y cancelas citas, y pasas a una persona del equipo los casos que lo requieren.

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
- Si la descripción de un servicio dice que requiere valoración previa (o que se cotiza en la valoración), no lo agendes directamente: explícalo y ofrece agendar tú misma la valoración (consulta la disponibilidad); no pases este caso al equipo.
- Nunca respondas "sí" o "claro" a un descuento, promoción o excepción que no esté en <negocio>; di que lo consultas con el equipo.
- Si el cliente pide un rango ("esta semana", "cualquier día en la tarde", "lo antes posible"), consulta tú la disponibilidad empezando por el día hábil más cercano y ofrece 2 o 3 opciones concretas. No pases al equipo solo porque no dio una fecha exacta.
- Si el mensaje trae una "Nota del sistema" con lo que escribió una persona del equipo, continúa con coherencia: no repitas lo que ya dijo ni lo contradigas, y no ofrezcas lo que ella ya resolvió.
- Si el mensaje empieza con 🎤, es una nota de voz transcrita automáticamente: puede tener errores (nombres, números, fechas). Antes de agendar, confirma con el paciente su nombre completo, la fecha y la hora que entendiste. No menciones la transcripción salvo que haga falta aclarar algo.
- No muestres al cliente números internos (id de cita, de caso, etc.).
- Si consultar_disponibilidad dice que el día es festivo, cerrado o está lleno, dilo y ofrece el siguiente día con cupo.
- Para ofrecer horarios usa siempre consultar_disponibilidad. Antes de agendar, confirma con el cliente servicio, fecha, hora y su nombre completo; luego usa agendar_cita y repite los datos de la cita confirmada con la dirección.
- Interpreta "mañana", "el viernes", etc. según la fecha del mensaje que aparece entre corchetes al inicio de cada mensaje del cliente. Esa marca la agrega el sistema; no la menciones.
- Si el cliente muestra interés pero no agenda, usa registrar_interes antes de despedirte.
- No ofrezcas acciones que no puedes hacer con tus herramientas (por ejemplo, llamar por teléfono); si el cliente pide algo así, ofrece pasar el caso al equipo.
{recordatorios}
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


def marca_tiempo(momento: datetime) -> str:
    return f"[Mensaje recibido el {DIAS_TEXTO[DIAS[momento.weekday()]].lower()} {momento:%Y-%m-%d} a las {momento:%H:%M}]"


class Asistente:
    def __init__(
        self,
        db: BaseDatos,
        cliente_api=None,
        ahora: Callable[[], datetime] = ahora_bogota,
        notificar_dueno: Callable[[Negocio, str], None] | None = None,
        proveedor: str | None = None,
    ):
        self.db = db
        self.motor = crear_motor(proveedor, cliente_api)
        self.ahora = ahora
        self.notificar_dueno = notificar_dueno

    def _clave(self, negocio: Negocio) -> str:
        # Cada proveedor guarda el historial en su propio formato.
        return negocio.id if self.motor.nombre == "claude" else f"{negocio.id}@{self.motor.nombre}"

    def _historial(self, negocio: Negocio, cliente: str) -> list[dict]:
        historial = self.db.historial(self._clave(negocio), cliente)
        ultimo = self.db.ultima_actividad(self._clave(negocio), cliente)
        inactivo = ultimo is not None and self.ahora() - ultimo > REINICIO_INACTIVIDAD
        if inactivo or len(historial) >= MAX_MENSAJES:
            return []
        return historial

    def _nota_equipo(self, negocio: Negocio, cliente: str) -> str:
        """Lo que pasó en el chat mientras el asistente estaba en pausa (la clínica atendió a mano)."""
        ultimo = self.db.ultima_actividad(self._clave(negocio), cliente)
        filas = self.db.mensajes_chat(negocio.id, cliente, ultimo.isoformat(timespec="seconds") if ultimo else "")[-10:]
        if not filas:
            return ""
        quien = {"equipo": "Una persona del equipo escribió", "asistente": "Tú (el asistente) enviaste"}
        lineas = [f'{quien.get(f["rol"], "El paciente escribió")}: "{f["texto"][:300]}"' for f in filas]
        return "[Nota del sistema, no la menciones: mientras no atendías este chat pasó lo siguiente. " + " / ".join(lineas) + "] "

    def responder(self, negocio: Negocio, cliente: str, texto: str) -> str:
        """Procesa un mensaje del cliente y devuelve el texto a enviarle."""
        momento = self.ahora()
        mensajes = self._historial(negocio, cliente)
        mensajes.append({"role": "user", "content": f"{self._nota_equipo(negocio, cliente)}{marca_tiempo(momento)} {texto}"})
        herramientas = Herramientas(self.db, negocio, cliente, self.ahora, self.notificar_dueno)
        try:
            respuesta = self.motor.turno(prompt_sistema(negocio), mensajes, herramientas)
        except FallaModelo as e:
            return self._fallar(negocio, cliente, str(e))
        self.db.guardar_historial(self._clave(negocio), cliente, mensajes, momento)
        return respuesta or RESPUESTA_FALLA

    def _fallar(self, negocio: Negocio, cliente: str, motivo: str) -> str:
        self.db.registrar_escalacion(negocio.id, cliente, f"Falla del asistente: {motivo}")
        if self.notificar_dueno:
            self.notificar_dueno(negocio, f"⚠️ El asistente no pudo responder a {cliente} ({motivo}).")
        return RESPUESTA_FALLA
