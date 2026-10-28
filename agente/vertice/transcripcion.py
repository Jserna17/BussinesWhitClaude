"""Convierte el historial guardado (formato Claude u OpenAI) en un chat legible para el panel."""

from __future__ import annotations

import json
import re

MARCA = re.compile(
    r"^\[Mensaje recibido el \S+ (\d{4}-\d{2}-\d{2}) a las (\d{2}:\d{2})\]\s*"
    r"(?:\(Nombre en WhatsApp: ([^)]*)\)\s*)?(.*)$",
    re.S,
)


def _evento(nombre: str, entrada: dict) -> str | None:
    """Texto corto para el médico cuando el asistente usó una herramienta."""
    if nombre == "agendar_cita":
        return f"Agendó {entrada.get('servicio', '')} · {entrada.get('fecha', '')} {entrada.get('hora', '')} · {entrada.get('nombre', '')}"
    if nombre == "reprogramar_cita":
        return f"Reprogramó la cita #{entrada.get('cita_id')} · {entrada.get('fecha', '')} {entrada.get('hora', '')}"
    if nombre == "cancelar_cita":
        return f"Canceló la cita #{entrada.get('cita_id')}"
    if nombre == "pasar_a_humano":
        return f"Pasó el caso al equipo: {entrada.get('motivo', '')}"
    if nombre == "registrar_interes":
        return f"Guardó interesado: {entrada.get('interes', '')}"
    if nombre == "consultar_disponibilidad":
        return f"Revisó la agenda del {entrada.get('fecha', '')}"
    return None


def leer(mensajes: list[dict]) -> dict:
    """Devuelve {"mensajes": [{rol, texto, fecha, hora}], "nombre_perfil": str}.
    rol: "paciente" | "asistente" | "evento"."""
    salida: list[dict] = []
    nombre_perfil = ""
    fecha = hora = ""
    # Resultado de cada herramienta, para no mostrar como hecho algo que el sistema rechazó.
    errores: dict[str, str] = {}
    for m in mensajes:
        if m.get("role") == "tool" and str(m.get("content", "")).startswith("ERROR:"):
            errores[m.get("tool_call_id", "")] = str(m["content"])[6:].strip()
        if m.get("role") == "user" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if b.get("type") == "tool_result" and b.get("is_error"):
                    errores[b.get("tool_use_id", "")] = str(b.get("content", ""))

    def evento(id_: str, nombre: str, entrada: dict) -> str:
        texto = _evento(nombre, entrada) or ""
        if id_ in errores and texto:
            if nombre == "consultar_disponibilidad":
                return ""
            accion = {"agendar_cita": "agendar", "cancelar_cita": "cancelar", "reprogramar_cita": "reprogramar"}.get(nombre, "hacer una acción")
            return f"Intentó {accion} y el sistema no lo permitió: {errores[id_].split('.')[0].split(';')[0]}."
        return texto

    def agregar(rol: str, texto: str):
        texto = (texto or "").strip()
        if texto:
            salida.append({"rol": rol, "texto": texto, "fecha": fecha, "hora": hora})

    for m in mensajes:
        rol, contenido = m.get("role"), m.get("content")
        if rol == "user" and isinstance(contenido, str):
            hallado = MARCA.match(contenido)
            if hallado:
                fecha, hora, perfil, texto = hallado.groups()
                nombre_perfil = perfil or nombre_perfil
            else:
                texto = contenido
            agregar("paciente", texto)
        elif rol == "assistant":
            if isinstance(contenido, list):  # Claude: bloques
                for b in contenido:
                    if b.get("type") == "text":
                        agregar("asistente", b.get("text", ""))
                    elif b.get("type") == "tool_use":
                        agregar("evento", evento(b.get("id", ""), b.get("name", ""), b.get("input") or {}))
            else:  # OpenAI
                agregar("asistente", contenido or "")
                for c in m.get("tool_calls") or []:
                    try:
                        entrada = json.loads(c["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        entrada = {}
                    agregar("evento", evento(c.get("id", ""), c["function"].get("name", ""), entrada))
    return {"mensajes": salida, "nombre_perfil": nombre_perfil}
