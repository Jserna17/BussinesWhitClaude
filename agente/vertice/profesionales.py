"""Odontólogos de cada clínica: validar, guardar y aplicar los cambios en vivo.

Los odontólogos viven en la base de datos y se administran desde el panel (Equipo). El archivo YAML de la clínica solo se usa
la PRIMERA vez que arranca el sistema (para sembrarlos); después, la base de datos manda y el YAML se ignora.
Los cambios se aplican al instante: se reemplaza la clínica en el diccionario compartido por el asistente, el panel y los recordatorios.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import replace

from .db import BaseDatos
from .negocio import DIAS, Negocio

log = logging.getLogger(__name__)
HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def a_dict(fila) -> dict:
    """Fila de la base -> formato que usa `Negocio.profesionales` ("servicios" y "horario" se omiten si no aplican)."""
    d = {"nombre": fila["nombre"]}
    servicios = json.loads(fila["servicios"])
    if servicios:
        d["servicios"] = servicios
    if fila["horario"]:
        d["horario"] = json.loads(fila["horario"])
    return d


def aplicar(db: BaseDatos, negocios: dict[str, Negocio], negocio_id: str) -> None:
    """Hace que asistente, panel y recordatorios vean ya la lista vigente de odontólogos activos de esa clínica."""
    activos = [a_dict(f) for f in db.profesionales_de(negocio_id) if f["activo"]]
    negocios[negocio_id] = replace(negocios[negocio_id], profesionales=activos)


def sincronizar(db: BaseDatos, negocios: dict[str, Negocio]) -> None:
    """Al arrancar: siembra desde el YAML las clínicas que aún no tienen odontólogos en la base; luego la base manda."""
    for n in list(negocios.values()):
        filas = db.profesionales_de(n.id)
        if not filas:
            for p in n.profesionales:
                horario = json.dumps({d: [list(f) for f in _franjas(v)] for d, v in p["horario"].items()}) if p.get("horario") else ""
                db.crear_profesional(n.id, p["nombre"], json.dumps(p.get("servicios") or []), horario)
        elif n.profesionales and [p["nombre"] for p in n.profesionales] != [f["nombre"] for f in filas if f["activo"]]:
            log.warning("[%s] El YAML lista otros odontólogos que la base de datos: manda la base (se administran desde el panel).", n.id)
        aplicar(db, negocios, n.id)


def _franjas(valor) -> list[tuple[str, str]]:
    valor = valor or []
    if valor and isinstance(valor[0], str):
        return [(valor[0], valor[1])]
    return [(a, b) for a, b in valor]


def validar_servicios(servicios: list[str], negocio: Negocio) -> list[str]:
    """[] = atiende todos. Cada nombre debe existir en la lista de servicios de la clínica."""
    existentes = {s.nombre for s in negocio.servicios}
    limpios = list(dict.fromkeys(s.strip() for s in servicios if s.strip()))
    desconocidos = [s for s in limpios if s not in existentes]
    if desconocidos:
        raise ValueError(f"Servicio desconocido: {', '.join(desconocidos)}.")
    if set(limpios) == existentes:
        return []  # los atiende todos: se guarda como "todos" para que los servicios nuevos que agregue la clínica también cuenten
    return limpios


def validar_horario(horario: dict | None) -> dict | None:
    """None = el horario de la clínica. Si no, {día: [[inicio, fin], ...]} con horas válidas, sin cruces y en orden."""
    if not horario:
        return None
    limpio: dict[str, list[list[str]]] = {}
    for dia, franjas in horario.items():
        if dia not in DIAS:
            raise ValueError(f"Día desconocido: {dia}.")
        orden = sorted([f[0], f[1]] for f in franjas)
        for inicio, fin in orden:
            if not (HORA.match(inicio) and HORA.match(fin)):
                raise ValueError(f"Hora inválida en {dia}: use el formato HH:MM.")
            if fin <= inicio:
                raise ValueError(f"En {dia}, la hora final debe ser posterior a la inicial.")
        for (_, fin_a), (ini_b, _) in zip(orden, orden[1:]):
            if ini_b < fin_a:
                raise ValueError(f"En {dia}, los turnos se cruzan.")
        if orden:
            limpio[dia] = orden
    if not limpio:
        raise ValueError("Marca al menos un día en el que atiende, o elige el horario de la clínica.")
    return limpio


def validar_nombre(nombre: str) -> str:
    nombre = " ".join(nombre.split())
    if not 3 <= len(nombre) <= 60:
        raise ValueError("El nombre debe tener entre 3 y 60 letras (ej.: Dra. Laura Gómez).")
    return nombre


def como_json(servicios: list[str], horario: dict | None) -> tuple[str, str]:
    return json.dumps(servicios, ensure_ascii=False), json.dumps(horario, ensure_ascii=False) if horario else ""
