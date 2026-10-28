"""Herramientas que el asistente puede usar: agenda, prospectos y traspaso a humano."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

from .agenda import Agenda, CitaNoEncontrada, Conflicto, ErrorAgenda
from .db import BaseDatos
from .negocio import DIAS, Negocio

MAX_HORARIOS = 24
NOMBRES_GENERICOS = {"cliente", "paciente", "usuario", "sin nombre", "nombre", "cliente nuevo", "paciente nuevo"}


def _esquema(propiedades: dict, requeridas: list[str]) -> dict:
    return {
        "type": "object",
        "properties": propiedades,
        "required": requeridas,
        "additionalProperties": False,
    }


# Lista fija y en orden determinista: cualquier cambio invalida la caché del prompt.
DEFINICIONES = [
    {
        "name": "consultar_disponibilidad",
        "description": (
            "Consulta los horarios libres del negocio para un servicio en una fecha. "
            "Úsala siempre antes de proponer u ofrecer horarios; nunca inventes disponibilidad."
        ),
        "strict": True,
        "input_schema": _esquema(
            {
                "fecha": {"type": "string", "description": "Fecha en formato AAAA-MM-DD."},
                "servicio": {"type": "string", "description": "Nombre del servicio tal como aparece en la lista."},
            },
            ["fecha", "servicio"],
        ),
    },
    {
        "name": "agendar_cita",
        "description": (
            "Agenda una cita confirmada. Úsala solo cuando el cliente ya eligió servicio, fecha y hora "
            "(de los horarios que devolvió consultar_disponibilidad) y dio su nombre."
        ),
        "strict": True,
        "input_schema": _esquema(
            {
                "nombre": {"type": "string", "description": "Nombre completo del cliente."},
                "servicio": {"type": "string"},
                "fecha": {"type": "string", "description": "AAAA-MM-DD"},
                "hora": {"type": "string", "description": "HH:MM en formato 24 horas."},
            },
            ["nombre", "servicio", "fecha", "hora"],
        ),
    },
    {
        "name": "ver_mis_citas",
        "description": "Muestra las próximas citas confirmadas de este cliente (identificado por su número).",
        "strict": True,
        "input_schema": _esquema({}, []),
    },
    {
        "name": "reprogramar_cita",
        "description": (
            "Cambia una cita confirmada del cliente a otra fecha u hora. Primero usa ver_mis_citas para obtener el id y "
            "consultar_disponibilidad para ofrecer horarios; confirma con el cliente el nuevo horario antes de usarla."
        ),
        "strict": True,
        "input_schema": _esquema(
            {
                "cita_id": {"type": "integer"},
                "fecha": {"type": "string", "description": "Nueva fecha AAAA-MM-DD."},
                "hora": {"type": "string", "description": "Nueva hora HH:MM en formato 24 horas."},
            },
            ["cita_id", "fecha", "hora"],
        ),
    },
    {
        "name": "confirmar_asistencia",
        "description": (
            "Registra que el cliente confirmó que asistirá a una cita (por ejemplo, responde \"sí, voy\" a un "
            "recordatorio). Usa ver_mis_citas para obtener el id; si tiene varias citas, confirma cuál."
        ),
        "strict": True,
        "input_schema": _esquema({"cita_id": {"type": "integer"}}, ["cita_id"]),
    },
    {
        "name": "cancelar_cita",
        "description": "Cancela una cita del cliente. Primero usa ver_mis_citas para obtener el id y confirma con el cliente.",
        "strict": True,
        "input_schema": _esquema({"cita_id": {"type": "integer"}}, ["cita_id"]),
    },
    {
        "name": "registrar_interes",
        "description": (
            "Guarda un prospecto cuando el cliente muestra interés en un servicio pero todavía no agenda "
            "(pide precios, dice que lo piensa, pregunta por financiación). Guarda su nombre si lo dio."
        ),
        "strict": True,
        "input_schema": _esquema(
            {
                "nombre": {"type": "string", "description": "Nombre del cliente o cadena vacía si no lo dio."},
                "interes": {"type": "string", "description": "Servicio o tema de interés."},
                "notas": {"type": "string", "description": "Detalles útiles para el seguimiento."},
            },
            ["nombre", "interes", "notas"],
        ),
    },
    {
        "name": "pasar_a_humano",
        "description": (
            "Avisa al equipo del negocio para que una persona continúe la conversación. Úsala en los casos "
            "listados en las reglas del negocio, si el cliente lo pide, o si no puedes resolver algo."
        ),
        "strict": True,
        "input_schema": _esquema(
            {"motivo": {"type": "string", "description": "Resumen breve del caso para el equipo."}},
            ["motivo"],
        ),
    },
]


class Herramientas:
    """Ejecuta las herramientas para un negocio y un cliente concretos."""

    def __init__(
        self,
        db: BaseDatos,
        negocio: Negocio,
        cliente: str,
        ahora: Callable[[], datetime] = datetime.now,
        notificar_dueno: Callable[[Negocio, str], None] | None = None,
    ):
        self.db = db
        self.negocio = negocio
        self.cliente = cliente
        self.ahora = ahora
        self.notificar_dueno = notificar_dueno
        self.agenda = Agenda(db, negocio, ahora)

    def ejecutar(self, nombre: str, entrada: dict) -> tuple[str, bool]:
        """Devuelve (contenido, es_error)."""
        funcion = getattr(self, f"_{nombre}", None)
        if funcion is None or nombre not in {d["name"] for d in DEFINICIONES}:
            return f"Herramienta desconocida: {nombre}", True
        try:
            return json.dumps(funcion(**entrada), ensure_ascii=False), False
        except ErrorHerramienta as e:
            return str(e), True

    # --- Agenda (reglas en vertice/agenda.py, compartidas con el panel) ---
    def _validar(self, servicio: str, fecha: str):
        try:
            s = self.agenda.servicio(servicio)
            dia = self.agenda.fecha(fecha)
        except ErrorAgenda as e:
            raise ErrorHerramienta(str(e))
        if s.requiere_valoracion:
            valoraciones = [x.nombre for x in self.negocio.servicios if "valoraci" in x.nombre.lower()]
            raise ErrorHerramienta(
                f"'{s.nombre}' requiere valoración previa y no se agenda directamente. "
                f"Ofrece agendar primero: {', '.join(valoraciones) or 'una valoración'}."
            )
        return s, dia

    def _consultar_disponibilidad(self, fecha: str, servicio: str) -> dict:
        s, dia = self._validar(servicio, fecha)
        libres = sorted(self.agenda.libres(dia, s))
        if not libres:
            motivo = self.agenda.cerrado(dia) or "No hay horarios libres ese día (agenda llena)."
            return {"fecha": fecha, "dia": DIAS[dia.weekday()], "horarios_libres": [],
                    "nota": f"{motivo} Ofrece otro día."}
        return {"fecha": fecha, "dia": DIAS[dia.weekday()], "servicio": s.nombre,
                "duracion_min": s.duracion_min,
                "manana": [h for h in libres if h < "12:00"][:MAX_HORARIOS],
                "tarde": [h for h in libres if h >= "12:00"][:MAX_HORARIOS],
                "horarios_libres": libres}

    def _agendar_cita(self, nombre: str, servicio: str, fecha: str, hora: str) -> dict:
        s, _ = self._validar(servicio, fecha)
        palabras = [p for p in nombre.replace(".", " ").split() if len(p) > 1]
        if len(palabras) < 2 or nombre.strip().lower() in NOMBRES_GENERICOS:
            raise ErrorHerramienta("Antes de agendar pide al cliente su nombre y apellido; no inventes ni uses "
                                   "nombres genéricos. Todavía no se agendó nada.")
        try:
            cita = self.agenda.reservar(self.cliente, nombre, s.nombre, fecha, hora)
        except Conflicto as e:
            raise ErrorHerramienta(f"{e} Otro paciente acaba de tomarla o no está libre. "
                                   "Consulta la disponibilidad de nuevo y ofrece otras horas.")
        except ErrorAgenda as e:
            raise ErrorHerramienta(str(e))
        if len(self.negocio.nombres_profesionales()) == 1:
            cita.pop("profesional")
        return cita

    def _ver_mis_citas(self) -> dict:
        citas = self.db.citas_de_cliente(self.negocio.id, self.cliente, self.ahora().isoformat(timespec="seconds"))
        return {"citas": [
            {"cita_id": c["id"], "servicio": c["servicio"], "inicio": c["inicio"], "nombre": c["nombre"]}
            for c in citas
        ]}

    def _reprogramar_cita(self, cita_id: int, fecha: str, hora: str) -> dict:
        try:
            cita = self.agenda.reprogramar(cita_id, fecha, hora, cliente=self.cliente)
        except CitaNoEncontrada as e:
            raise ErrorHerramienta(str(e))
        except Conflicto as e:
            raise ErrorHerramienta(f"{e} No se movió nada: la cita sigue en su horario original. "
                                   "Consulta la disponibilidad de nuevo y ofrece otras horas.")
        except ErrorAgenda as e:
            raise ErrorHerramienta(str(e))
        if len(self.negocio.nombres_profesionales()) == 1:
            cita.pop("profesional")
        return cita

    def _confirmar_asistencia(self, cita_id: int) -> dict:
        if not self.db.marcar_confirmacion(self.negocio.id, cita_id, self.cliente, "confirmo"):
            raise ErrorHerramienta("No encontré una cita confirmada con ese id para este cliente.")
        return {"cita_id": cita_id, "asistencia_confirmada": True}

    def _cancelar_cita(self, cita_id: int) -> dict:
        if not self.db.cancelar_cita(self.negocio.id, self.cliente, cita_id):
            raise ErrorHerramienta("No encontré una cita confirmada con ese id para este cliente.")
        return {"cita_id": cita_id, "estado": "cancelada"}

    # --- Prospectos y traspaso -----------------------------------------
    def _registrar_interes(self, nombre: str, interes: str, notas: str) -> dict:
        pid = self.db.registrar_prospecto(self.negocio.id, self.cliente, nombre, interes, notas)
        return {"prospecto_id": pid, "guardado": True}

    def _pasar_a_humano(self, motivo: str) -> dict:
        eid = self.db.registrar_escalacion(self.negocio.id, self.cliente, motivo)
        if self.notificar_dueno:
            self.notificar_dueno(self.negocio, f"🔔 Caso para atender (cliente {self.cliente}): {motivo}")
        return {"caso_id": eid, "equipo_notificado": True,
                "nota": "Dile al cliente que una persona del equipo le escribirá pronto."}


class ErrorHerramienta(Exception):
    pass
