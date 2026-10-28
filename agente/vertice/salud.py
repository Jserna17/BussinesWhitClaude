"""Salud del sistema: qué medir y cuándo algo merece una alerta.

`recolectar` junta las señales (las lee el monitoreo desde la misma base de datos); `evaluar` las convierte en alertas
legibles para quien opera Vértice. Las alertas se pensaron para detectar lo que en la práctica deja a una clínica sin servicio
sin que nadie lo note: el token de WhatsApp vencido, el modelo de IA caído, el servidor detenido o sin copias de seguridad.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .db import BaseDatos
from .negocio import Negocio

# Umbrales (se pueden ajustar al llamar a `evaluar`)
UMBRALES = {"fallos_hora": 3, "sin_mensajes_h": 36, "ciclo_recordatorios_min": 20, "espera_equipo_min": 120,
            "disco_libre_pct": 15.0, "respaldo_h": 26}


def _edad_min(iso: str | None, ahora: datetime) -> int | None:
    if not iso:
        return None
    return max(0, int((ahora - datetime.fromisoformat(iso)).total_seconds() // 60))


def _leer(ruta: Path) -> str | None:
    try:
        return ruta.read_text().strip() or None
    except OSError:
        return None


def ultimo_respaldo(carpeta: str | Path) -> str | None:
    """Fecha del respaldo más reciente (por la fecha del archivo) o None si no hay."""
    archivos = [f for f in Path(carpeta).glob("vertice-*.db*") if f.is_file()] if carpeta else []
    if not archivos:
        return None
    return datetime.fromtimestamp(max(f.stat().st_mtime for f in archivos)).isoformat(timespec="seconds")


def recolectar(db: BaseDatos, negocios: dict[str, Negocio], ahora: datetime, ruta_respaldos: str = "",
               ruta_db: str | Path = "") -> dict:
    hora = (ahora - timedelta(hours=1)).isoformat(timespec="seconds")
    dia = (ahora - timedelta(hours=24)).isoformat(timespec="seconds")
    casos = [c for n in negocios for c in db.filas("escalaciones", n) if c["estado"] == "abierta"]
    solicitudes = [c for n in negocios for c in db.citas_entre(n, ahora.isoformat(timespec="minutes"), "9999") if c["estado"] == "por_confirmar"]
    disco = shutil.disk_usage(str(ruta_db) if ruta_db and Path(ruta_db).exists() else ".")
    return {
        "hora": ahora.isoformat(timespec="seconds"),
        "ultimo_webhook": db.estado("ultimo_webhook"),
        "ultimo_ciclo_recordatorios": db.estado("ultimo_ciclo_recordatorios"),
        "fallos_ultima_hora": db.fallos_desde(hora),
        "fallos_24h": db.fallos_desde(dia),
        "casos_abiertos": len(casos),
        "caso_mas_antiguo_min": max((_edad_min(c["creado"], ahora) for c in casos), default=None),
        "solicitudes_pendientes": len(solicitudes),
        "solicitud_mas_antigua_min": max((_edad_min(c["creado"], ahora) for c in solicitudes), default=None),
        "disco_libre_pct": round(100 * disco.free / disco.total, 1),
        "db_mb": round(Path(ruta_db).stat().st_size / 1e6, 2) if ruta_db and Path(ruta_db).exists() else None,
        "respaldos_configurados": bool(ruta_respaldos),
        "ultimo_respaldo": ultimo_respaldo(ruta_respaldos) if ruta_respaldos else None,
        "subida_configurada": bool(os.environ.get("VERTICE_RESPALDO_SUBIR")),
        "ultima_subida": _leer(Path(ruta_respaldos) / "subida_ok.txt") if ruta_respaldos else None,
    }


def evaluar(d: dict, ahora: datetime, umbrales: dict | None = None) -> dict[str, str]:
    """{clave_de_alerta: mensaje}. Cada clave identifica el problema para no repetir el aviso ni perder la recuperación."""
    u = {**UMBRALES, **(umbrales or {})}
    alertas: dict[str, str] = {}
    f = d["fallos_ultima_hora"]
    if f.get("envio", 0) >= u["fallos_hora"]:
        alertas["envio"] = f"WhatsApp rechazó {f['envio']} envíos en la última hora. ¿Venció el token de acceso o se bloqueó el número?"
    if f.get("modelo", 0) >= u["fallos_hora"]:
        alertas["modelo"] = f"El modelo de IA falló {f['modelo']} veces en la última hora (saldo, límite o caída del proveedor)."
    if f.get("atender", 0) >= 1:
        alertas["atender"] = f"{f['atender']} mensajes de pacientes fallaron por un error del sistema en la última hora (quedaron como casos para atender a mano)."
    if f.get("firma", 0) >= 1:
        alertas["firma"] = f"{f['firma']} webhooks con firma inválida: puede haber cambiado el secreto de la app en Meta, o alguien intenta enviar mensajes falsos."
    if f.get("recordatorio", 0) >= u["fallos_hora"]:
        alertas["recordatorio"] = f"{f['recordatorio']} recordatorios fallaron en la última hora (¿plantilla sin aprobar o rechazada?)."
    edad_webhook = _edad_min(d["ultimo_webhook"], ahora)
    if edad_webhook is not None and edad_webhook > u["sin_mensajes_h"] * 60:
        alertas["sin_mensajes"] = (f"No llega ningún mensaje de WhatsApp hace {edad_webhook // 60} h. "
                                   "Revisa que el webhook siga activo en Meta y que el servidor sea alcanzable.")
    edad_ciclo = _edad_min(d["ultimo_ciclo_recordatorios"], ahora)
    if edad_ciclo is not None and edad_ciclo > u["ciclo_recordatorios_min"]:
        alertas["ciclo"] = f"El ciclo de recordatorios no corre hace {edad_ciclo} minutos (¿el servicio se detuvo?)."
    if (d["caso_mas_antiguo_min"] or 0) > u["espera_equipo_min"]:
        alertas["casos"] = f"Hay casos sin atender hace {d['caso_mas_antiguo_min'] // 60} h ({d['casos_abiertos']} abiertos)."
    if (d["solicitud_mas_antigua_min"] or 0) > u["espera_equipo_min"]:
        alertas["solicitudes"] = f"Hay solicitudes de cita sin confirmar hace {d['solicitud_mas_antigua_min'] // 60} h ({d['solicitudes_pendientes']} pendientes)."
    if d["disco_libre_pct"] < u["disco_libre_pct"]:
        alertas["disco"] = f"Queda poco espacio en el disco del servidor ({d['disco_libre_pct']} % libre)."
    if d["respaldos_configurados"]:
        edad_respaldo = _edad_min(d["ultimo_respaldo"], ahora)
        if edad_respaldo is None:
            alertas["respaldo"] = "Los respaldos están configurados pero todavía no existe ninguno."
        elif edad_respaldo > u["respaldo_h"] * 60:
            alertas["respaldo"] = f"El último respaldo es de hace {edad_respaldo // 60} h (debería ser diario)."
        if d.get("subida_configurada"):
            edad_subida = _edad_min(d.get("ultima_subida"), ahora)
            if edad_subida is None or edad_subida > u["respaldo_h"] * 60:
                alertas["respaldo_remoto"] = "El respaldo no se está copiando a otro lugar: si el servidor se pierde, se pierden los datos."
    return alertas
