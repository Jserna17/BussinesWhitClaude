"""Servidor web: recibe el webhook de WhatsApp y responde con el asistente.

Ejecutar:  uvicorn vertice.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from . import recordatorios, voz, whatsapp
from .agente import Asistente
from .db import BaseDatos
from .negocio import Negocio, cargar_negocios
from .panel import montar_panel

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("vertice")

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_NEGOCIOS = Path(os.environ.get("VERTICE_NEGOCIOS", RAIZ / "negocios"))
RUTA_DB = os.environ.get("VERTICE_DB", RAIZ / "vertice.db")
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")

NO_TEXTO = "Por ahora solo puedo leer mensajes de texto y notas de voz ✍️ ¿Me escribes tu consulta?"
INTERVALO_RECORDATORIOS = int(os.environ.get("VERTICE_RECORDATORIOS_SEGUNDOS", "300"))
NO_ENTENDI_VOZ = "No logré escuchar bien tu nota de voz 🎧 ¿Me la puedes escribir, por favor?"


def notificar_dueno(negocio: Negocio, texto: str) -> None:
    if negocio.telefono_dueno and negocio.whatsapp_phone_number_id:
        whatsapp.enviar_texto(negocio.whatsapp_phone_number_id, negocio.telefono_dueno, texto)
    else:
        log.warning("[%s] Aviso para el equipo (sin número configurado): %s", negocio.id, texto)


def crear_app(asistente: Asistente | None = None, negocios: dict[str, Negocio] | None = None,
              enviar=whatsapp.enviar_texto, descargar=whatsapp.descargar_media, transcribir=voz.transcribir,
              enviar_plantilla=whatsapp.enviar_plantilla, recordatorios_activos: bool | None = None) -> FastAPI:
    db = BaseDatos(RUTA_DB) if asistente is None else asistente.db
    asistente = asistente or Asistente(db, notificar_dueno=notificar_dueno)
    negocios = negocios if negocios is not None else cargar_negocios(CARPETA_NEGOCIOS)
    por_numero = {n.whatsapp_phone_number_id: n for n in negocios.values() if n.whatsapp_phone_number_id}

    if recordatorios_activos is None:
        recordatorios_activos = os.environ.get("VERTICE_RECORDATORIOS", "1") != "0"

    def enviar_recordatorios() -> dict:
        return recordatorios.ciclo(db, negocios, enviar_plantilla, asistente.ahora())

    @asynccontextmanager
    async def vida(_app: FastAPI):
        async def bucle():
            while True:
                try:
                    r = await asyncio.to_thread(enviar_recordatorios)
                    if r["enviados"] or r["fallidos"]:
                        log.info("Recordatorios: %s", r)
                except Exception:  # noqa: BLE001 - el ciclo nunca debe morir
                    log.exception("Falló el ciclo de recordatorios")
                await asyncio.sleep(INTERVALO_RECORDATORIOS)
        tarea = asyncio.create_task(bucle()) if recordatorios_activos else None
        yield
        if tarea:
            tarea.cancel()

    app = FastAPI(title="Vértice · Asistente de WhatsApp", lifespan=vida)
    app.state.enviar_recordatorios = enviar_recordatorios
    montar_panel(app, db, negocios, asistente.ahora, enviar)

    @app.get("/salud")
    def salud():
        return {"ok": True, "negocios": sorted(negocios)}

    @app.get("/webhook")
    def verificar(request: Request):
        q = request.query_params
        if q.get("hub.mode") == "subscribe" and VERIFY_TOKEN and q.get("hub.verify_token") == VERIFY_TOKEN:
            return PlainTextResponse(q.get("hub.challenge", ""))
        raise HTTPException(status_code=403)

    def enviar_y_registrar(negocio: Negocio, para: str, texto: str) -> None:
        wamid = enviar(negocio.whatsapp_phone_number_id, para, texto)
        if wamid:
            db.marcar_procesado(wamid)  # si Meta lo "ecoa" de vuelta no es un mensaje del equipo

    def texto_de(m: whatsapp.MensajeEntrante, negocio: Negocio) -> str | None:
        """Texto del mensaje; las notas de voz se transcriben (con 🎤 delante para que el asistente lo sepa)."""
        if m.tipo == "audio" and m.media_id:
            try:
                audio, mime = descargar(m.media_id)
                return "🎤 " + transcribir(audio, m.mime or mime)
            except Exception as e:  # noqa: BLE001 - no se pudo: se le pide que escriba
                log.error("[%s] No se pudo transcribir la nota de voz de %s: %s", negocio.id, m.de, e)
                return None
        return m.texto

    def respuesta_a_boton(m: whatsapp.MensajeEntrante, negocio: Negocio) -> str | None:
        """Botones del recordatorio. Devuelve el texto para el asistente, "" si ya se resolvió sola, None si no aplica."""
        accion, _, cid = m.payload.partition(":")
        if accion not in ("confirmar", "cambiar") or not cid.isdigit():
            return None
        cita = db.cita(negocio.id, int(cid))
        if cita is None or cita["estado"] != "confirmada" or cita["cliente"] != m.de:
            return None  # la cita ya no existe o se canceló: que lo atienda el asistente como texto normal
        db.marcar_confirmacion(negocio.id, int(cid), m.de, "confirmo" if accion == "confirmar" else "cambiar")
        cuando = recordatorios.cuando(datetime.fromisoformat(cita["inicio"]), asistente.ahora())
        if accion == "cambiar":
            return f"Necesito cambiar mi cita de {cita['servicio']} ({cuando})."
        db.guardar_mensaje_chat(negocio.id, m.de, "paciente", "✅ Confirmó su asistencia", "whatsapp")
        if not db.pausa_vigente(negocio.id, m.de):
            gracias = f"¡Gracias, {cita['nombre'].split()[0]}! Quedó confirmada tu asistencia {cuando} ✅ Si algo cambia, escríbenos por aquí."
            db.guardar_mensaje_chat(negocio.id, m.de, "asistente", gracias, "recordatorio")
            enviar_y_registrar(negocio, m.de, gracias)
        return ""

    def atender(m: whatsapp.MensajeEntrante, negocio: Negocio) -> None:
        if m.payload:
            traducido = respuesta_a_boton(m, negocio)
            if traducido == "":
                return
            if traducido:
                m = whatsapp.MensajeEntrante(**{**m.__dict__, "texto": traducido, "tipo": "text", "payload": ""})
        texto_entrante = texto_de(m, negocio)
        if db.pausa_vigente(negocio.id, m.de):
            # Una persona atiende este chat: guardamos el mensaje para que el equipo lo vea y no respondemos.
            db.guardar_mensaje_chat(negocio.id, m.de, "paciente", texto_entrante or f"[{m.tipo}]", "whatsapp")
            return
        if texto_entrante is None:
            enviar_y_registrar(negocio, m.de, NO_ENTENDI_VOZ if m.tipo == "audio" else NO_TEXTO)
            return
        texto = texto_entrante if not m.nombre_perfil else f"(Nombre en WhatsApp: {m.nombre_perfil}) {texto_entrante}"
        respuesta = asistente.responder(negocio, m.de, texto)
        enviar_y_registrar(negocio, m.de, respuesta)

    @app.post("/webhook")
    async def recibir(request: Request, tareas: BackgroundTasks):
        cuerpo = await request.body()
        if APP_SECRET and not whatsapp.firma_valida(cuerpo, request.headers.get("X-Hub-Signature-256"), APP_SECRET):
            raise HTTPException(status_code=401)
        payload = json.loads(cuerpo or b"{}")
        for e in whatsapp.extraer_ecos(payload):
            negocio = por_numero.get(e.phone_number_id)
            if negocio is None or not e.para or (e.id and not db.marcar_procesado(e.id)):
                continue
            db.guardar_mensaje_chat(negocio.id, e.para, "equipo", e.texto, "app")
            db.pausar(negocio.id, e.para, negocio.pausa_horas, "El equipo escribió desde la app de WhatsApp")
        for m in whatsapp.extraer_mensajes(payload):
            negocio = por_numero.get(m.phone_number_id)
            if negocio is None:
                log.warning("Mensaje para un número no configurado: %s", m.phone_number_id)
                continue
            if not db.marcar_procesado(m.id):
                continue  # Meta reintenta entregas: no responder dos veces
            tareas.add_task(atender, m, negocio)
        return {"ok": True}  # responder rápido; Meta reintenta si tardamos

    return app


def __getattr__(nombre: str):
    # `uvicorn vertice.app:app` crea la app al importarla (no al importar el módulo en pruebas).
    if nombre == "app":
        global app
        app = crear_app()
        return app
    raise AttributeError(nombre)
