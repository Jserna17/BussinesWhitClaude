"""Motores de IA intercambiables. Cada uno ejecuta un turno completo (con herramientas) sobre
el historial en su propio formato. Se elige con VERTICE_PROVEEDOR = claude | openai."""

from __future__ import annotations

import json
import logging
import os

from .herramientas import DEFINICIONES, Herramientas

log = logging.getLogger(__name__)

MAX_VUELTAS = 8


class FallaModelo(Exception):
    """El modelo no pudo responder (error de API, conexión o rechazo)."""


class MotorClaude:
    nombre = "claude"

    def __init__(self, cliente=None):
        import anthropic

        self._anthropic = anthropic
        self.api = cliente or anthropic.Anthropic()
        self.modelo = os.environ.get("VERTICE_MODELO", "claude-opus-5-5")
        self.esfuerzo = os.environ.get("VERTICE_ESFUERZO", "low")  # chat corto: low suele bastar

    def turno(self, sistema: str, mensajes: list[dict], herramientas: Herramientas) -> str:
        texto_final = ""
        for _ in range(MAX_VUELTAS):
            try:
                respuesta = self.api.beta.messages.create(
                    model=self.modelo,
                    max_tokens=16000,
                    **respaldo(self.modelo),
                    output_config={"effort": self.esfuerzo},
                    cache_control={"type": "ephemeral"},
                    system=[{"type": "text", "text": sistema}],
                    tools=DEFINICIONES,
                    messages=mensajes,
                )
            except self._anthropic.APIStatusError as e:
                log.error("Error de la API de Claude (%s): %s", e.status_code, e.message)
                raise FallaModelo(f"error de la API {e.status_code}")
            except self._anthropic.APIConnectionError:
                log.exception("Sin conexión con la API de Claude")
                raise FallaModelo("sin conexión con la API")

            uso = respuesta.usage
            log.info("tokens entrada=%s cache_leidos=%s salida=%s parada=%s",
                     uso.input_tokens, uso.cache_read_input_tokens, uso.output_tokens, respuesta.stop_reason)
            if respuesta.stop_reason == "refusal":
                raise FallaModelo("el modelo no pudo responder este mensaje")

            # Se guarda el contenido completo (incluidos bloques de razonamiento) sin modificarlo.
            mensajes.append({"role": "assistant", "content": [b.to_dict() for b in respuesta.content]})
            texto_final = "\n".join(b.text for b in respuesta.content if b.type == "text").strip()

            usos = [b for b in respuesta.content if b.type == "tool_use"]
            if respuesta.stop_reason != "tool_use" or not usos:
                return texto_final

            resultados = []
            for u in usos:
                contenido, es_error = herramientas.ejecutar(u.name, u.input)
                log.info("herramienta %s -> %s", u.name, contenido[:200])
                resultados.append({"type": "tool_result", "tool_use_id": u.id,
                                   "content": contenido, "is_error": es_error})
            mensajes.append({"role": "user", "content": resultados})
        log.warning("Se alcanzó el máximo de vueltas")
        return texto_final


def respaldo(modelo: str) -> dict:
    """Si el modelo rechaza un mensaje por seguridad, la API lo reintenta en otro modelo.
    Haiku no tiene respaldo en el servidor (con él se omite el parámetro)."""
    if modelo.startswith("claude-haiku"):
        return {}
    return {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}


# Mismas herramientas en el formato de funciones de OpenAI.
HERRAMIENTAS_OPENAI = [
    {"type": "function", "function": {
        "name": d["name"], "description": d["description"],
        "parameters": d["input_schema"], "strict": True,
    }}
    for d in DEFINICIONES
]


class MotorOpenAI:
    nombre = "openai"

    def __init__(self, cliente=None):
        import openai

        self._openai = openai
        self.api = cliente or openai.OpenAI()
        self.modelo = os.environ.get("VERTICE_MODELO_OPENAI", "gpt-5-mini")

    def turno(self, sistema: str, mensajes: list[dict], herramientas: Herramientas) -> str:
        texto_final = ""
        for _ in range(MAX_VUELTAS):
            try:
                respuesta = self.api.chat.completions.create(
                    model=self.modelo,
                    messages=[{"role": "system", "content": sistema}, *mensajes],
                    tools=HERRAMIENTAS_OPENAI,
                )
            except self._openai.APIStatusError as e:
                log.error("Error de la API de OpenAI (%s): %s", e.status_code, e.message)
                raise FallaModelo(f"error de la API {e.status_code}")
            except self._openai.APIConnectionError:
                log.exception("Sin conexión con la API de OpenAI")
                raise FallaModelo("sin conexión con la API")

            if respuesta.usage:
                log.info("tokens entrada=%s salida=%s", respuesta.usage.prompt_tokens,
                         respuesta.usage.completion_tokens)
            eleccion = respuesta.choices[0]
            mensaje = eleccion.message
            if getattr(mensaje, "refusal", None):
                raise FallaModelo("el modelo no pudo responder este mensaje")

            llamadas = mensaje.tool_calls or []
            guardado = {"role": "assistant", "content": mensaje.content or ""}
            if llamadas:
                guardado["tool_calls"] = [
                    {"id": c.id, "type": "function",
                     "function": {"name": c.function.name, "arguments": c.function.arguments}}
                    for c in llamadas
                ]
            mensajes.append(guardado)
            texto_final = (mensaje.content or "").strip()
            if not llamadas:
                return texto_final

            for c in llamadas:
                try:
                    entrada = json.loads(c.function.arguments or "{}")
                    contenido, es_error = herramientas.ejecutar(c.function.name, entrada)
                except json.JSONDecodeError:
                    contenido, es_error = "Argumentos inválidos (JSON mal formado).", True
                log.info("herramienta %s -> %s", c.function.name, contenido[:200])
                mensajes.append({"role": "tool", "tool_call_id": c.id,
                                 "content": f"ERROR: {contenido}" if es_error else contenido})
        log.warning("Se alcanzó el máximo de vueltas")
        return texto_final


def crear_motor(proveedor: str | None = None, cliente=None):
    proveedor = (proveedor or os.environ.get("VERTICE_PROVEEDOR", "claude")).lower()
    if proveedor == "openai":
        return MotorOpenAI(cliente)
    if proveedor == "claude":
        return MotorClaude(cliente)
    raise ValueError(f"Proveedor desconocido: {proveedor} (usa 'claude' u 'openai')")
