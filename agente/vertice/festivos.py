"""Festivos de Colombia (Ley 51 de 1983, "Ley Emiliani"), calculados para cualquier año.

- Fijos: 1 ene, 1 may, 20 jul, 7 ago, 8 dic, 25 dic.
- Se corren al lunes siguiente: 6 ene, 19 mar, 29 jun, 15 ago, 12 oct, 1 nov, 11 nov.
- Según la Pascua: Jueves y Viernes Santo (no se corren); Ascensión, Corpus Christi y Sagrado Corazón (lunes).
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

FIJOS = [((1, 1), "Año Nuevo"), ((5, 1), "Día del Trabajo"), ((7, 20), "Día de la Independencia"),
         ((8, 7), "Batalla de Boyacá"), ((12, 8), "Inmaculada Concepción"), ((12, 25), "Navidad")]
TRASLADABLES = [((1, 6), "Reyes Magos"), ((3, 19), "San José"), ((6, 29), "San Pedro y San Pablo"),
                ((8, 15), "Asunción de la Virgen"), ((10, 12), "Día de la Raza"), ((11, 1), "Todos los Santos"),
                ((11, 11), "Independencia de Cartagena")]


def pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo de Butcher/Meeus, calendario gregoriano)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(anio, mes, dia)


def _lunes_siguiente(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7)


@lru_cache(maxsize=None)
def festivos(anio: int) -> dict[date, str]:
    resultado = {date(anio, m, d): nombre for (m, d), nombre in FIJOS}
    for (m, d), nombre in TRASLADABLES:
        resultado[_lunes_siguiente(date(anio, m, d))] = nombre
    p = pascua(anio)
    resultado[p - timedelta(days=3)] = "Jueves Santo"
    resultado[p - timedelta(days=2)] = "Viernes Santo"
    resultado[_lunes_siguiente(p + timedelta(days=39))] = "Ascensión del Señor"
    resultado[_lunes_siguiente(p + timedelta(days=60))] = "Corpus Christi"
    resultado[_lunes_siguiente(p + timedelta(days=68))] = "Sagrado Corazón"
    return dict(sorted(resultado.items()))


def festivo(dia: date) -> str | None:
    """Nombre del festivo o None."""
    return festivos(dia.year).get(dia)
