"""Configuración de cada negocio cliente (multi-cliente: un archivo YAML por negocio)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DIAS_TEXTO = {"lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
              "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo"}


@dataclass(frozen=True)
class Servicio:
    nombre: str
    precio: str
    duracion_min: int
    descripcion: str = ""
    requiere_valoracion: bool = False  # no se agenda directo: primero la valoración


@dataclass(frozen=True)
class Negocio:
    id: str
    nombre: str
    tipo: str
    ciudad: str
    direccion: str
    telefono_dueno: str
    horario: dict[str, list[str]]  # "lunes": ["08:00", "18:00"]; día sin entrada = cerrado
    servicios: list[Servicio]
    faq: list[dict[str, str]] = field(default_factory=list)
    politicas: list[str] = field(default_factory=list)
    pasar_a_humano_si: list[str] = field(default_factory=list)
    tono: str = "cercano y profesional"
    nombre_asistente: str = "Asistente"
    whatsapp_phone_number_id: str = ""

    def servicio(self, nombre: str) -> Servicio | None:
        buscado = nombre.strip().lower()
        for s in self.servicios:
            if s.nombre.lower() == buscado:
                return s
        for s in self.servicios:
            if buscado in s.nombre.lower() or s.nombre.lower() in buscado:
                return s
        return None


def cargar_negocio(ruta: Path) -> Negocio:
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    datos["servicios"] = [Servicio(**s) for s in datos["servicios"]]
    datos["whatsapp_phone_number_id"] = str(datos.get("whatsapp_phone_number_id") or "")
    datos["telefono_dueno"] = str(datos.get("telefono_dueno") or "")
    return Negocio(**datos)


def cargar_negocios(carpeta: Path) -> dict[str, Negocio]:
    negocios = {}
    for ruta in sorted(carpeta.glob("*.yaml")):
        n = cargar_negocio(ruta)
        negocios[n.id] = n
    return negocios
