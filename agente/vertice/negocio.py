"""Configuración de cada negocio cliente (multi-cliente: un archivo YAML por negocio)."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
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
    # Sillas/odontólogos que atienden en paralelo. Vacío = un solo consultorio.
    # Cada uno: {"nombre": "Dra. Ana", "servicios": [...]} (sin "servicios" = atiende todo).
    profesionales: list[dict] = field(default_factory=list)
    anticipacion_min: int = 60   # el asistente no ofrece horarios que empiecen antes de esto
    intervalo_min: int = 30      # cada cuánto empieza un turno
    panel_clave: str = ""        # clave del panel del médico (o variable VERTICE_PANEL_CLAVE_<ID>)

    def franjas(self, dia: str) -> list[tuple[str, str]]:
        """Franjas de atención de un día: ["08:00","18:00"] o [["08:00","12:00"],["14:00","18:00"]]."""
        valor = self.horario.get(dia) or []
        if valor and isinstance(valor[0], str):
            return [(valor[0], valor[1])]
        return [(a, b) for a, b in valor]

    def nombres_profesionales(self, servicio: str | None = None) -> list[str]:
        if not self.profesionales:
            return ["Consultorio"]
        return [p["nombre"] for p in self.profesionales
                if servicio is None or not p.get("servicios") or servicio in p["servicios"]]

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
    datos["panel_clave"] = str(datos.get("panel_clave") or os.environ.get(f"VERTICE_PANEL_CLAVE_{datos['id'].upper().replace('-', '_')}", ""))
    return Negocio(**datos)


def cargar_negocios(carpeta: Path) -> dict[str, Negocio]:
    negocios = {}
    for ruta in sorted(carpeta.glob("*.yaml")):
        n = cargar_negocio(ruta)
        negocios[n.id] = n
    return negocios
