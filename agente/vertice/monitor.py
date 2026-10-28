"""Monitoreo: se ejecuta cada 5 minutos en el servidor (ver despliegue/) y avisa al operador si algo anda mal.

    python -m vertice.monitor

Variables:  VERTICE_ALERTA_URL  donde se envían los avisos. Con ntfy.sh (gratis, sin cuenta: https://ntfy.sh/<tema-secreto>) llegan
                                al celular con la app ntfy; con un webhook de Slack/Discord llegan como mensaje en un canal.
            VERTICE_URL_PUBLICA dirección pública del servidor (para comprobar que responde desde afuera).
            VERTICE_RESPALDOS   carpeta de los respaldos (para vigilar que sean diarios).
Cada problema se avisa una vez y se repite cada 6 h mientras siga; cuando se resuelve llega un aviso de "recuperado".
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Callable

from . import salud
from .db import BaseDatos
from .negocio import Negocio

log = logging.getLogger("vertice.monitor")
REPETIR = timedelta(hours=6)


def enviar_alerta_http(url: str, texto: str) -> None:
    """ntfy recibe el texto tal cual; Slack/Discord/otros reciben JSON con "text" y "content"."""
    if "ntfy" in url:
        cuerpo, cabeceras = texto.encode(), {"Title": "Vértice", "Priority": "high"}
    else:
        cuerpo, cabeceras = json.dumps({"text": texto, "content": texto}).encode(), {"Content-Type": "application/json"}
    urllib.request.urlopen(urllib.request.Request(url, data=cuerpo, headers=cabeceras, method="POST"), timeout=15).close()


def servidor_responde(url: str) -> bool:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/salud", timeout=10) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def ejecutar(db: BaseDatos, negocios: dict[str, Negocio], ahora: datetime, enviar_alerta: Callable[[str], None],
             ruta_respaldos: str = "", ruta_db: str = "", url_publica: str = "",
             responde: Callable[[str], bool] = servidor_responde, umbrales: dict | None = None) -> dict[str, str]:
    """Evalúa la salud y envía avisos nuevos o recuperaciones. Devuelve las alertas activas."""
    datos = salud.recolectar(db, negocios, ahora, ruta_respaldos, ruta_db)
    alertas = salud.evaluar(datos, ahora, umbrales)
    if url_publica and not responde(url_publica):
        alertas["caido"] = f"El servidor no responde en {url_publica}."
    previas = json.loads(db.estado("alertas_activas") or "{}")  # {clave: iso del último aviso}
    nuevas: dict[str, str] = {}
    for clave, mensaje in alertas.items():
        ultimo = previas.get(clave)
        if ultimo is None or ahora - datetime.fromisoformat(ultimo) >= REPETIR:
            enviar_alerta(f"🔴 {mensaje}")
            nuevas[clave] = ahora.isoformat(timespec="seconds")
        else:
            nuevas[clave] = ultimo
    for clave in previas.keys() - alertas.keys():
        enviar_alerta(f"✅ Recuperado: {clave}")
    db.poner_estado("alertas_activas", json.dumps(nuevas))
    db.poner_estado("ultimo_monitoreo", ahora.isoformat(timespec="seconds"))
    return alertas


def main() -> int:
    from .agente import ahora_bogota
    from .app import CARPETA_NEGOCIOS, RUTA_DB
    from .negocio import cargar_negocios
    url = os.environ.get("VERTICE_ALERTA_URL", "")

    def enviar(texto: str) -> None:
        print(texto)
        if url:
            try:
                enviar_alerta_http(url, texto)
            except Exception as e:  # noqa: BLE001 - si no se puede avisar, al menos queda en el registro
                log.error("No se pudo enviar el aviso: %s", e)

    alertas = ejecutar(BaseDatos(RUTA_DB), cargar_negocios(CARPETA_NEGOCIOS), ahora_bogota().replace(tzinfo=None), enviar,
                       os.environ.get("VERTICE_RESPALDOS", ""), str(RUTA_DB), os.environ.get("VERTICE_URL_PUBLICA", ""))
    return 1 if alertas else 0


if __name__ == "__main__":
    sys.exit(main())
