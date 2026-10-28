"""Recordatorios de cita por WhatsApp con botones "Confirmo" / "Necesito cambiarla".

Dos avisos por cita: el del día anterior (hasta 24 h antes) y uno corto de 2 h antes. Reglas para no molestar:
- Nunca de noche: el primero solo entre las 8:00 y las 19:59 y el segundo entre las 7:00 y las 19:59.
- Si la cita se agendó hace poco (ya está fresca en la cabeza del paciente) no se manda el aviso que le queda pegado.
- Cada aviso se reserva en la base antes de enviarse: dos procesos nunca lo envían dos veces; si falla, se reintenta.
- Solo a pacientes con número de WhatsApp real (las citas de recepción sin teléfono se omiten).
Los envíos fuera de la ventana de 24 h de WhatsApp requieren una plantilla aprobada por Meta (ver
`plantillas/plantillas-whatsapp-meta.md`).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Callable

from .db import BaseDatos
from .negocio import DIAS, DIAS_TEXTO, Negocio

log = logging.getLogger(__name__)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def cuando(inicio: datetime, ahora: datetime) -> str:
    """'hoy a las 2:00 p. m.', 'mañana a las 8:30 a. m.' o 'el jueves 29 de octubre a las 2:00 p. m.'."""
    hora12 = inicio.hour % 12 or 12
    hora = f"{hora12}:{inicio:%M} {'a. m.' if inicio.hour < 12 else 'p. m.'}"
    dias = (inicio.date() - ahora.date()).days
    if dias == 0:
        return f"hoy a las {hora}"
    if dias == 1:
        return f"mañana a las {hora}"
    dia = DIAS_TEXTO[DIAS[inicio.weekday()]].lower()
    return f"el {dia} {inicio.day} de {MESES[inicio.month - 1]} a las {hora}"


def _es_telefono(cliente: str) -> bool:
    return cliente.isdigit() and len(cliente) >= 10


def toca_recordatorio(cita, numero: int, ahora: datetime) -> bool:
    inicio = datetime.fromisoformat(cita["inicio"])
    creado = datetime.fromisoformat(cita["creado"])
    falta = inicio - ahora
    if numero == 1:
        return (timedelta(hours=4) < falta <= timedelta(hours=24) and 8 <= ahora.hour < 20
                and creado <= inicio - timedelta(hours=24))  # agendada con más de un día de anticipación
    return (timedelta(minutes=30) < falta <= timedelta(hours=2) and 7 <= ahora.hour < 20
            and inicio - creado >= timedelta(hours=6))


def ciclo(db: BaseDatos, negocios: dict[str, Negocio], enviar_plantilla: Callable, ahora: datetime) -> dict:
    """Envía los recordatorios que toquen ahora. Devuelve {'enviados': n, 'fallidos': n}."""
    resultado = {"enviados": 0, "fallidos": 0}
    for n in negocios.values():
        if not (n.recordatorios and n.whatsapp_phone_number_id):
            continue
        desde = ahora.isoformat(timespec="seconds")
        hasta = (ahora + timedelta(hours=24, minutes=1)).isoformat(timespec="seconds")
        for cita in db.citas_entre(n.id, desde, hasta):
            if cita["estado"] != "confirmada" or not _es_telefono(cita["cliente"]):
                continue
            for numero in (1, 2):
                if cita[f"recordatorio_{numero}"] or not toca_recordatorio(cita, numero, ahora):
                    continue
                if not db.reclamar_recordatorio(cita["id"], numero):
                    continue  # otro proceso ya lo tomó
                nombre = cita["nombre"].replace("Paciente ejemplo · ", "").split()[0]
                try:
                    wamid = enviar_plantilla(
                        n.whatsapp_phone_number_id, cita["cliente"], n.plantilla_recordatorio,
                        [nombre, n.nombre, cita["servicio"], cuando(datetime.fromisoformat(cita["inicio"]), ahora)],
                        [f"confirmar:{cita['id']}", f"cambiar:{cita['id']}"])
                except Exception as e:  # noqa: BLE001 - se reintenta en el siguiente ciclo
                    db.liberar_recordatorio(cita["id"], numero)
                    db.registrar_fallo(n.id, "recordatorio", f"cita {cita['id']}: {e}")
                    resultado["fallidos"] += 1
                    log.error("[%s] Recordatorio %s de la cita %s no se pudo enviar: %s", n.id, numero, cita["id"], e)
                    continue
                if wamid:
                    db.marcar_procesado(wamid)
                resultado["enviados"] += 1
                break  # un recordatorio por cita en cada ciclo
    return resultado
