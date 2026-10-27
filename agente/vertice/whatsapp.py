"""Cloud API de WhatsApp (Meta): verificar firmas, leer mensajes entrantes y enviar respuestas."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

log = logging.getLogger(__name__)

GRAPH_VERSION = os.environ.get("WHATSAPP_GRAPH_VERSION", "v23.0")


@dataclass(frozen=True)
class MensajeEntrante:
    id: str
    phone_number_id: str  # número del negocio que recibió el mensaje
    de: str  # número del cliente (formato internacional sin +)
    nombre_perfil: str
    texto: str | None  # None si no es texto (audio, imagen, ubicación…)
    tipo: str


def firma_valida(cuerpo: bytes, firma_cabecera: str | None, app_secret: str) -> bool:
    """Valida la cabecera X-Hub-Signature-256 que Meta envía en cada webhook."""
    if not firma_cabecera or not firma_cabecera.startswith("sha256="):
        return False
    esperada = hmac.new(app_secret.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, firma_cabecera.removeprefix("sha256="))


def extraer_mensajes(payload: dict) -> list[MensajeEntrante]:
    mensajes = []
    for entrada in payload.get("entry", []):
        for cambio in entrada.get("changes", []):
            valor = cambio.get("value", {})
            phone_number_id = str(valor.get("metadata", {}).get("phone_number_id", ""))
            nombres = {c.get("wa_id"): c.get("profile", {}).get("name", "") for c in valor.get("contacts", [])}
            for m in valor.get("messages", []):
                tipo = m.get("type", "")
                texto = m.get("text", {}).get("body") if tipo == "text" else None
                if tipo == "button":
                    texto = m.get("button", {}).get("text")
                mensajes.append(MensajeEntrante(
                    id=m.get("id", ""), phone_number_id=phone_number_id, de=m.get("from", ""),
                    nombre_perfil=nombres.get(m.get("from"), ""), texto=texto, tipo=tipo,
                ))
    return mensajes


def enviar_texto(phone_number_id: str, para: str, texto: str, token: str | None = None) -> None:
    token = token or os.environ["WHATSAPP_TOKEN"]
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{phone_number_id}/messages"
    cuerpo = json.dumps({
        "messaging_product": "whatsapp",
        "to": para,
        "type": "text",
        "text": {"body": texto[:4096], "preview_url": False},
    }).encode()
    peticion = urllib.request.Request(
        url, data=cuerpo, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=15) as r:
            log.info("WhatsApp enviado a %s (%s)", para, r.status)
    except urllib.error.HTTPError as e:
        log.error("WhatsApp rechazó el envío a %s: %s %s", para, e.code, e.read()[:300])
