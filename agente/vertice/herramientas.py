"""Herramientas que el asistente puede usar: agenda, prospectos y traspaso a humano."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Callable

from .db import BaseDatos
from .negocio import DIAS, Negocio

INTERVALO_MIN = 30
MAX_HORARIOS = 24


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

    def ejecutar(self, nombre: str, entrada: dict) -> tuple[str, bool]:
        """Devuelve (contenido, es_error)."""
        funcion = getattr(self, f"_{nombre}", None)
        if funcion is None or nombre not in {d["name"] for d in DEFINICIONES}:
            return f"Herramienta desconocida: {nombre}", True
        try:
            return json.dumps(funcion(**entrada), ensure_ascii=False), False
        except ErrorHerramienta as e:
            return str(e), True

    # --- Agenda ---------------------------------------------------------
    def _horarios_libres(self, fecha: date, duracion: int) -> list[str]:
        dia = DIAS[fecha.weekday()]
        franjas = self.negocio.horario.get(dia)
        if not franjas:
            return []
        apertura = datetime.combine(fecha, datetime.strptime(franjas[0], "%H:%M").time())
        cierre = datetime.combine(fecha, datetime.strptime(franjas[1], "%H:%M").time())
        ocupadas = [
            (datetime.fromisoformat(c["inicio"]), datetime.fromisoformat(c["fin"]))
            for c in self.db.citas_del_dia(self.negocio.id, fecha.isoformat())
        ]
        minimo = self.ahora() + timedelta(hours=1)
        libres = []
        inicio = apertura
        while inicio + timedelta(minutes=duracion) <= cierre:
            fin = inicio + timedelta(minutes=duracion)
            choca = any(inicio < o_fin and fin > o_ini for o_ini, o_fin in ocupadas)
            if not choca and inicio >= minimo:
                libres.append(inicio.strftime("%H:%M"))
            inicio += timedelta(minutes=INTERVALO_MIN)
        return libres

    def _validar(self, servicio: str, fecha: str):
        s = self.negocio.servicio(servicio)
        if s is None:
            nombres = ", ".join(x.nombre for x in self.negocio.servicios)
            raise ErrorHerramienta(f"Servicio '{servicio}' no existe. Servicios disponibles: {nombres}.")
        try:
            dia = date.fromisoformat(fecha)
        except ValueError:
            raise ErrorHerramienta("Fecha inválida; usa el formato AAAA-MM-DD.")
        if dia < self.ahora().date():
            raise ErrorHerramienta("Esa fecha ya pasó.")
        if s.requiere_valoracion:
            valoraciones = [x.nombre for x in self.negocio.servicios if "valoraci" in x.nombre.lower()]
            raise ErrorHerramienta(
                f"'{s.nombre}' requiere valoración previa y no se agenda directamente. "
                f"Ofrece agendar primero: {', '.join(valoraciones) or 'una valoración'}."
            )
        return s, dia

    def _consultar_disponibilidad(self, fecha: str, servicio: str) -> dict:
        s, dia = self._validar(servicio, fecha)
        libres = self._horarios_libres(dia, s.duracion_min)
        if not libres:
            return {"fecha": fecha, "dia": DIAS[dia.weekday()], "horarios_libres": [],
                    "nota": "No hay horarios libres ese día (cerrado o lleno). Ofrece otro día."}
        return {"fecha": fecha, "dia": DIAS[dia.weekday()], "servicio": s.nombre,
                "duracion_min": s.duracion_min,
                "manana": [h for h in libres if h < "12:00"][:MAX_HORARIOS],
                "tarde": [h for h in libres if h >= "12:00"][:MAX_HORARIOS],
                "horarios_libres": libres}

    def _agendar_cita(self, nombre: str, servicio: str, fecha: str, hora: str) -> dict:
        s, dia = self._validar(servicio, fecha)
        if not nombre.strip():
            raise ErrorHerramienta("Falta el nombre del cliente.")
        if hora not in self._horarios_libres(dia, s.duracion_min):
            raise ErrorHerramienta(
                f"La hora {hora} no está disponible el {fecha}. Consulta la disponibilidad de nuevo."
            )
        inicio = datetime.combine(dia, datetime.strptime(hora, "%H:%M").time())
        fin = inicio + timedelta(minutes=s.duracion_min)
        cita_id = self.db.crear_cita(
            self.negocio.id, self.cliente, nombre.strip(), s.nombre, inicio.isoformat(), fin.isoformat()
        )
        return {"cita_id": cita_id, "estado": "confirmada", "servicio": s.nombre,
                "fecha": fecha, "dia": DIAS[dia.weekday()], "hora": hora,
                "direccion": self.negocio.direccion}

    def _ver_mis_citas(self) -> dict:
        citas = self.db.citas_de_cliente(self.negocio.id, self.cliente)
        return {"citas": [
            {"cita_id": c["id"], "servicio": c["servicio"], "inicio": c["inicio"], "nombre": c["nombre"]}
            for c in citas
        ]}

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
