"""Servidor web: recibe el webhook de WhatsApp y responde con el asistente.

Ejecutar:  uvicorn vertice.app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from . import whatsapp
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

NO_TEXTO = "Por ahora solo puedo leer mensajes de texto ✍️ ¿Me escribes tu consulta?"


def notificar_dueno(negocio: Negocio, texto: str) -> None:
    if negocio.telefono_dueno and negocio.whatsapp_phone_number_id:
        whatsapp.enviar_texto(negocio.whatsapp_phone_number_id, negocio.telefono_dueno, texto)
    else:
        log.warning("[%s] Aviso para el equipo (sin número configurado): %s", negocio.id, texto)


def crear_app(asistente: Asistente | None = None, negocios: dict[str, Negocio] | None = None,
              enviar=whatsapp.enviar_texto) -> FastAPI:
    db = BaseDatos(RUTA_DB) if asistente is None else asistente.db
    asistente = asistente or Asistente(db, notificar_dueno=notificar_dueno)
    negocios = negocios if negocios is not None else cargar_negocios(CARPETA_NEGOCIOS)
    por_numero = {n.whatsapp_phone_number_id: n for n in negocios.values() if n.whatsapp_phone_number_id}

    app = FastAPI(title="Vértice · Asistente de WhatsApp")
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

    def atender(m: whatsapp.MensajeEntrante, negocio: Negocio) -> None:
        if db.pausa_vigente(negocio.id, m.de):
            # Una persona atiende este chat: guardamos el mensaje para que el equipo lo vea y no respondemos.
            db.guardar_mensaje_chat(negocio.id, m.de, "paciente", m.texto or f"[{m.tipo}]", "whatsapp")
            return
        if m.texto is None:
            enviar_y_registrar(negocio, m.de, NO_TEXTO)
            return
        texto = m.texto if not m.nombre_perfil else f"(Nombre en WhatsApp: {m.nombre_perfil}) {m.texto}"
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
