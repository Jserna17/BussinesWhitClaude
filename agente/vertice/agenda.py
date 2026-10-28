"""Motor de agenda: qué horarios están libres y cómo reservar sin cruces.

Lo usan el asistente (herramientas) y el panel del médico, así ambos aplican exactamente las mismas reglas.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable

from .db import BaseDatos, Conflicto
from .festivos import festivo
from .negocio import DIAS, Negocio, Servicio

__all__ = ["Agenda", "Conflicto", "ErrorAgenda"]


class ErrorAgenda(Exception):
    """Pedido inválido (servicio inexistente, fecha pasada, fuera de horario…)."""


def _hora(dia: date, hhmm: str) -> datetime:
    return datetime.combine(dia, datetime.strptime(hhmm, "%H:%M").time())


class Agenda:
    def __init__(self, db: BaseDatos, negocio: Negocio, ahora: Callable[[], datetime] = datetime.now):
        self.db = db
        self.negocio = negocio
        self.ahora = ahora

    def servicio(self, nombre: str) -> Servicio:
        s = self.negocio.servicio(nombre)
        if s is None:
            nombres = ", ".join(x.nombre for x in self.negocio.servicios)
            raise ErrorAgenda(f"Servicio '{nombre}' no existe. Servicios disponibles: {nombres}.")
        return s

    def fecha(self, texto: str) -> date:
        try:
            dia = date.fromisoformat(texto)
        except ValueError:
            raise ErrorAgenda("Fecha inválida; usa el formato AAAA-MM-DD.")
        if dia < self.ahora().date():
            raise ErrorAgenda("Esa fecha ya pasó.")
        return dia

    def cerrado(self, dia: date) -> str | None:
        """Motivo por el que la clínica no atiende ese día (festivo o día sin horario), o None."""
        nombre = festivo(dia)
        if nombre and not self.negocio.abre_festivos:
            return f"Es festivo ({nombre}); la clínica no atiende."
        if not any(self.negocio.franjas_de(p, DIAS[dia.weekday()]) for p in self.negocio.nombres_profesionales()):
            return "La clínica no atiende ese día de la semana."
        return None

    def libres(self, dia: date, servicio: Servicio, anticipacion_min: int | None = None) -> dict[str, list[str]]:
        """{hora: [profesionales libres]} para cada turno en el que cabe el servicio completo."""
        if self.cerrado(dia):
            return {}
        anticipacion = self.negocio.anticipacion_min if anticipacion_min is None else anticipacion_min
        profesionales = self.negocio.nombres_profesionales(servicio.nombre)
        inicio_dia, fin_dia = _hora(dia, "00:00"), _hora(dia, "00:00") + timedelta(days=1)
        ocupado = self.db.ocupaciones(self.negocio.id, inicio_dia.isoformat(), fin_dia.isoformat())
        ocupado = [(o["profesional"], datetime.fromisoformat(o["inicio"]), datetime.fromisoformat(o["fin"]))
                   for o in ocupado]
        minimo = self.ahora() + timedelta(minutes=anticipacion)
        paso, dur = timedelta(minutes=self.negocio.intervalo_min), timedelta(minutes=servicio.duracion_min)
        resultado: dict[str, list[str]] = {}
        for prof in profesionales:  # cada profesional con su propio horario
            for desde, hasta in self.negocio.franjas_de(prof, DIAS[dia.weekday()]):
                t, cierre = _hora(dia, desde), _hora(dia, hasta)
                while t + dur <= cierre:
                    fin = t + dur
                    if t >= minimo and not any(p in ("", prof) and t < b and fin > a for p, a, b in ocupado):
                        resultado.setdefault(t.strftime("%H:%M"), []).append(prof)
                    t += paso
        return dict(sorted(resultado.items()))

    def reservar(self, cliente: str, nombre: str, servicio_nombre: str, fecha: str, hora: str,
                 profesional: str = "", origen: str = "asistente", anticipacion_min: int | None = None) -> dict:
        """Valida y reserva. Lanza Conflicto si el horario se ocupó; ErrorAgenda si el pedido es inválido."""
        s = self.servicio(servicio_nombre)
        dia = self.fecha(fecha)
        if not nombre.strip():
            raise ErrorAgenda("Falta el nombre del paciente.")
        hora = hora.strip().zfill(5)
        libres = self.libres(dia, s, anticipacion_min)
        if hora not in libres:
            raise Conflicto(f"La hora {hora} no está disponible el {fecha}.")
        candidatos = libres[hora]
        if profesional:
            if profesional not in candidatos:
                raise Conflicto(f"{profesional} no está libre a las {hora} el {fecha}.")
            candidatos = [profesional]
        inicio = _hora(dia, hora)
        fin = inicio + timedelta(minutes=s.duracion_min)
        # La reserva vuelve a comprobar dentro de una transacción exclusiva (dos pacientes a la vez).
        cita_id, prof = self.db.reservar(self.negocio.id, candidatos, cliente, nombre.strip(), s.nombre,
                                         inicio.isoformat(), fin.isoformat(), origen)
        return {"cita_id": cita_id, "estado": "confirmada", "servicio": s.nombre, "fecha": fecha,
                "dia": DIAS[dia.weekday()], "hora": hora, "profesional": prof, "direccion": self.negocio.direccion}
