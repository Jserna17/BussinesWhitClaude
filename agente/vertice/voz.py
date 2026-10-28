"""Notas de voz: se descargan de WhatsApp y se transcriben a texto para que el asistente las entienda.

La API de Claude no recibe audio, así que la transcripción usa la de OpenAI (OPENAI_API_KEY) sea cual sea el motor
de conversación. El modelo se puede cambiar con VERTICE_TRANSCRIPCION_MODELO.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

MODELO = os.environ.get("VERTICE_TRANSCRIPCION_MODELO", "gpt-4o-mini-transcribe")
MAX_BYTES = 5 * 1024 * 1024  # una nota de voz larga no se procesa: se le pide al paciente que la escriba
EXTENSIONES = {"audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/aac": "m4a", "audio/amr": "amr",
               "audio/wav": "wav", "audio/webm": "webm"}
PISTA = "Conversación por WhatsApp con una clínica dental en Colombia: citas, valoración, limpieza, ortodoncia, precios."


class ErrorVoz(Exception):
    """No se pudo descargar o transcribir la nota de voz."""


def transcribir(audio: bytes, mime: str = "audio/ogg", cliente=None, modelo: str | None = None) -> str:
    if len(audio) > MAX_BYTES:
        raise ErrorVoz("La nota de voz es demasiado larga.")
    mime_base = (mime or "audio/ogg").split(";")[0].strip().lower()
    extension = EXTENSIONES.get(mime_base, "ogg")
    try:
        if cliente is None:
            import openai
            cliente = openai.OpenAI()
        r = cliente.audio.transcriptions.create(model=modelo or MODELO, file=(f"nota.{extension}", audio, mime_base),
                                                language="es", prompt=PISTA)
    except Exception as e:  # noqa: BLE001 - cualquier falla del proveedor se trata igual
        raise ErrorVoz(f"Falló la transcripción: {e}") from e
    texto = (getattr(r, "text", None) or "").strip()
    if not texto:
        raise ErrorVoz("La transcripción salió vacía.")
    return texto
