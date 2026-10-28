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
    media_id: str = ""  # nota de voz: id para descargarla
    mime: str = ""


@dataclass(frozen=True)
class EcoEnviado:
    """Mensaje que una persona de la clínica escribió desde la app de WhatsApp Business (coexistencia)."""
    id: str
    phone_number_id: str
    para: str  # número del paciente
    texto: str


def extraer_ecos(payload: dict) -> list[EcoEnviado]:
    """Webhook `smb_message_echoes` de Meta. Formato según la documentación de coexistencia; se lee de forma
    tolerante (destinatario en `to` o `recipient_id`) y debe confirmarse con el primer número real conectado."""
    ecos = []
    for entrada in payload.get("entry", []):
        for cambio in entrada.get("changes", []):
            if cambio.get("field") != "smb_message_echoes":
                continue
            valor = cambio.get("value", {})
            phone_number_id = str(valor.get("metadata", {}).get("phone_number_id", ""))
            for m in valor.get("message_echoes", []):
                tipo = m.get("type", "")
                texto = m.get("text", {}).get("body", "") if tipo == "text" else f"[{tipo or 'mensaje'}]"
                ecos.append(EcoEnviado(id=m.get("id", ""), phone_number_id=phone_number_id,
                                       para=str(m.get("to") or m.get("recipient_id") or ""), texto=texto))
    return ecos


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
                audio = m.get("audio", {}) if tipo == "audio" else {}
                mensajes.append(MensajeEntrante(
                    id=m.get("id", ""), phone_number_id=phone_number_id, de=m.get("from", ""),
                    nombre_perfil=nombres.get(m.get("from"), ""), texto=texto, tipo=tipo,
                    media_id=str(audio.get("id", "")), mime=audio.get("mime_type", ""),
                ))
    return mensajes


def descargar_media(media_id: str, token: str | None = None) -> tuple[bytes, str]:
    """Descarga un archivo (nota de voz) de WhatsApp: primero se pide la URL y luego el contenido, ambos con el token."""
    token = token or os.environ["WHATSAPP_TOKEN"]
    cab = {"Authorization": f"Bearer {token}"}
    with urllib.request.urlopen(urllib.request.Request(f"https://graph.facebook.com/{GRAPH_VERSION}/{media_id}", headers=cab), timeout=15) as r:
        info = json.load(r)
    with urllib.request.urlopen(urllib.request.Request(info["url"], headers=cab), timeout=30) as r:
        return r.read(), info.get("mime_type", "audio/ogg")


def enviar_texto(phone_number_id: str, para: str, texto: str, token: str | None = None) -> str | None:
    """Envía un texto. Devuelve el id del mensaje en WhatsApp (para no confundirlo con un mensaje del equipo)."""
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
            try:
                return json.load(r)["messages"][0]["id"]
            except (KeyError, IndexError, ValueError):
                return None
    except urllib.error.HTTPError as e:
        log.error("WhatsApp rechazó el envío a %s: %s %s", para, e.code, e.read()[:300])
        raise
