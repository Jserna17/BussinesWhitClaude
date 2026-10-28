"""Panel del médico: indicadores, agenda sin cruces, conversaciones, casos e interesados.

Se monta en la misma app del webhook: GET /panel (página) y /panel/api/... (datos).
Acceso: cada negocio tiene su clave (`panel_clave` en el YAML o VERTICE_PANEL_CLAVE_<ID>); la página la envía
en las cabeceras X-Negocio y X-Clave.
"""

from __future__ import annotations

import hmac
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import transcripcion
from .agenda import Agenda, Conflicto, ErrorAgenda
from .db import ESTADOS_CITA, BaseDatos
from .festivos import festivos
from .negocio import DIAS, Negocio

PAGINA = Path(__file__).with_name("panel.html")


class NuevaCita(BaseModel):
    nombre: str
    telefono: str = ""
    servicio: str
    fecha: str
    hora: str
    profesional: str = ""


class NuevoEstado(BaseModel):
    estado: str


class NuevoBloqueo(BaseModel):
    fecha: str
    fecha_fin: str = ""  # para vacaciones o congresos de varios días (incluido)
    desde: str
    hasta: str
    profesional: str = ""
    motivo: str = ""


def _en_horario(negocio: Negocio, fecha: str, hora: str) -> bool:
    try:
        dia = DIAS[date.fromisoformat(fecha).weekday()]
    except ValueError:
        return True
    return any(a <= hora < b for a, b in negocio.franjas(dia))


def montar_panel(app: FastAPI, db: BaseDatos, negocios: dict[str, Negocio],
                 ahora: Callable[[], datetime] = datetime.now) -> None:
    api = APIRouter(prefix="/panel/api")

    def negocio_autorizado(x_negocio: str = Header(""), x_clave: str = Header("")) -> Negocio:
        n = negocios.get(x_negocio)
        if n is None or not n.panel_clave or not hmac.compare_digest(n.panel_clave, x_clave):
            raise HTTPException(status_code=401, detail="Clínica o clave incorrecta.")
        return n

    def claves(n: Negocio) -> list[str]:
        return [n.id, f"{n.id}@openai"]

    def conversaciones_leidas(n: Negocio) -> list[dict]:
        por_cliente: dict[str, dict] = {}
        for fila in db.conversaciones(claves(n)):
            leido = transcripcion.leer(json.loads(fila["mensajes"]))
            actual = por_cliente.get(fila["cliente"])
            if actual is None or fila["actualizado"] > actual["actualizado"]:
                por_cliente[fila["cliente"]] = {"cliente": fila["cliente"], "actualizado": fila["actualizado"], **leido}
        return sorted(por_cliente.values(), key=lambda c: c["actualizado"], reverse=True)

    def nombres_por_cliente(n: Negocio) -> dict[str, str]:
        nombres = {}
        for p in db.filas("prospectos", n.id):
            if p["nombre"]:
                nombres[p["cliente"]] = p["nombre"]
        for c in db.con.execute("SELECT cliente, nombre FROM citas WHERE negocio_id=? ORDER BY creado", (n.id,)):
            nombres[c["cliente"]] = c["nombre"]
        return nombres

    @api.get("/sesion")
    def sesion(n: Negocio = Depends(negocio_autorizado)):
        return {"negocio": n.id, "nombre": n.nombre, "asistente": n.nombre_asistente,
                "servicios": [s.nombre for s in n.servicios], "profesionales": n.nombres_profesionales(),
                "horario": {d: n.franjas(d) for d in DIAS}, "hoy": ahora().date().isoformat(),
                "horario_profesionales": {p: {d: n.franjas_de(p, d) for d in DIAS} for p in n.nombres_profesionales()},
                "abre_festivos": n.abre_festivos,
                "festivos": {d.isoformat(): nombre for a in (ahora().year, ahora().year + 1)
                             for d, nombre in festivos(a).items()}}

    @api.get("/resumen")
    def resumen(dias: int = 7, n: Negocio = Depends(negocio_autorizado)):
        hoy = ahora().date()
        desde = hoy - timedelta(days=dias - 1)
        convs = conversaciones_leidas(n)
        mensajes = [m for c in convs for m in c["mensajes"] if m["rol"] == "paciente" and m["fecha"] >= desde.isoformat()]
        fuera = sum(1 for m in mensajes if not _en_horario(n, m["fecha"], m["hora"]))
        por_dia = Counter(m["fecha"] for m in mensajes)
        citas_periodo = db.citas_entre(n.id, "0000", "9999")
        creadas = [c for c in citas_periodo if c["creado"][:10] >= desde.isoformat()]
        por_asistente = [c for c in creadas if c["origen"] == "asistente" and c["estado"] != "cancelada"]
        citas_por_dia = Counter(c["creado"][:10] for c in por_asistente)
        pasadas = [c for c in citas_periodo if c["estado"] in ("asistio", "no_asistio")]
        proximas = [dict(c) for c in citas_periodo
                    if c["estado"] == "confirmada" and c["inicio"] >= ahora().isoformat(timespec="minutes")]
        casos = [dict(c) for c in db.filas("escalaciones", n.id) if c["estado"] == "abierta"]
        interesados = db.filas("prospectos", n.id, desde.isoformat())
        return {
            "periodo": {"desde": desde.isoformat(), "hasta": hoy.isoformat(), "dias": dias},
            "conversaciones": sum(1 for c in convs if c["actualizado"][:10] >= desde.isoformat()),
            "mensajes_pacientes": len(mensajes),
            "fuera_de_horario": fuera,
            "citas_agendadas_asistente": len(por_asistente),
            "citas_hoy": sum(1 for c in citas_periodo if c["inicio"][:10] == hoy.isoformat() and c["estado"] != "cancelada"),
            "proximas": proximas[:8],
            "inasistencia": {"asistio": sum(1 for c in pasadas if c["estado"] == "asistio"),
                             "no_asistio": sum(1 for c in pasadas if c["estado"] == "no_asistio")},
            "casos_abiertos": len(casos),
            "interesados": len(interesados),
            "serie": [{"fecha": (desde + timedelta(days=i)).isoformat(),
                       "mensajes": por_dia.get((desde + timedelta(days=i)).isoformat(), 0),
                       "citas": citas_por_dia.get((desde + timedelta(days=i)).isoformat(), 0)}
                      for i in range(dias)],
        }

    @api.get("/agenda")
    def agenda(desde: str = "", dias: int = 7, n: Negocio = Depends(negocio_autorizado)):
        inicio = date.fromisoformat(desde) if desde else ahora().date()
        fin = inicio + timedelta(days=dias)
        citas = [dict(c) for c in db.citas_entre(n.id, inicio.isoformat(), fin.isoformat())]
        bloqueos = [dict(b) for b in db.bloqueos_entre(n.id, inicio.isoformat(), fin.isoformat())]
        return {"desde": inicio.isoformat(), "dias": dias, "citas": citas, "bloqueos": bloqueos}

    @api.get("/disponibilidad")
    def disponibilidad(fecha: str, servicio: str, n: Negocio = Depends(negocio_autorizado)):
        ag = Agenda(db, n, ahora)
        try:
            libres = ag.libres(ag.fecha(fecha), ag.servicio(servicio), anticipacion_min=0)
        except ErrorAgenda as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"fecha": fecha, "libres": libres}

    @api.post("/citas")
    def crear_cita(datos: NuevaCita, n: Negocio = Depends(negocio_autorizado)):
        cliente = "".join(ch for ch in datos.telefono if ch.isdigit()) or f"panel-{ahora():%Y%m%d%H%M%S}"
        try:
            return Agenda(db, n, ahora).reservar(cliente, datos.nombre, datos.servicio, datos.fecha, datos.hora,
                                                 datos.profesional, origen="panel", anticipacion_min=0)
        except Conflicto as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ErrorAgenda as e:
            raise HTTPException(status_code=400, detail=str(e))

    @api.post("/citas/{cita_id}/estado")
    def estado_cita(cita_id: int, datos: NuevoEstado, n: Negocio = Depends(negocio_autorizado)):
        if datos.estado not in ESTADOS_CITA:
            raise HTTPException(status_code=400, detail="Estado inválido.")
        if not db.cambiar_estado_cita(n.id, cita_id, datos.estado):
            raise HTTPException(status_code=404, detail="Cita no encontrada.")
        return {"ok": True}

    @api.post("/bloqueos")
    def crear_bloqueo(datos: NuevoBloqueo, n: Negocio = Depends(negocio_autorizado)):
        try:
            dia = date.fromisoformat(datos.fecha)
            ultimo = date.fromisoformat(datos.fecha_fin) if datos.fecha_fin else dia
            inicio = datetime.combine(dia, datetime.strptime(datos.desde, "%H:%M").time())
            fin = datetime.combine(ultimo, datetime.strptime(datos.hasta, "%H:%M").time())
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha u horas inválidas.")
        if fin <= inicio:
            raise HTTPException(status_code=400, detail="El final del bloqueo debe ser posterior al inicio.")
        if (ultimo - dia).days > 60:
            raise HTTPException(status_code=400, detail="Un bloqueo puede durar máximo 60 días.")
        if datos.profesional and datos.profesional not in n.nombres_profesionales():
            raise HTTPException(status_code=400, detail="Profesional desconocido.")
        bid = db.crear_bloqueo(n.id, datos.profesional, inicio.isoformat(), fin.isoformat(), datos.motivo)
        # Citas ya confirmadas dentro del bloqueo: hay que reprogramarlas (el bloqueo no las borra).
        afectadas = [dict(c) for c in db.citas_entre(n.id, inicio.isoformat(), fin.isoformat())
                     if c["estado"] == "confirmada" and c["fin"] > inicio.isoformat()
                     and (not datos.profesional or c["profesional"] == datos.profesional)]
        return {"bloqueo_id": bid, "citas_afectadas": afectadas}

    @api.delete("/bloqueos/{bloqueo_id}")
    def borrar_bloqueo(bloqueo_id: int, n: Negocio = Depends(negocio_autorizado)):
        if not db.borrar_bloqueo(n.id, bloqueo_id):
            raise HTTPException(status_code=404, detail="Bloqueo no encontrado.")
        return {"ok": True}

    @api.get("/conversaciones")
    def conversaciones(n: Negocio = Depends(negocio_autorizado)):
        nombres = nombres_por_cliente(n)
        casos = {c["cliente"] for c in db.filas("escalaciones", n.id) if c["estado"] == "abierta"}
        con_cita = {c["cliente"] for c in db.citas_entre(n.id, "0000", "9999") if c["estado"] == "confirmada"}
        lista = []
        for c in conversaciones_leidas(n):
            ultimo = next((m for m in reversed(c["mensajes"]) if m["rol"] != "evento"), None)
            lista.append({"cliente": c["cliente"], "nombre": nombres.get(c["cliente"]) or c["nombre_perfil"],
                          "actualizado": c["actualizado"], "ultimo": ultimo,
                          "mensajes": sum(1 for m in c["mensajes"] if m["rol"] == "paciente"),
                          "caso_abierto": c["cliente"] in casos, "tiene_cita": c["cliente"] in con_cita})
        return lista

    @api.get("/conversaciones/{cliente}")
    def conversacion(cliente: str, n: Negocio = Depends(negocio_autorizado)):
        for c in conversaciones_leidas(n):
            if c["cliente"] == cliente:
                return {**c, "nombre": nombres_por_cliente(n).get(cliente) or c["nombre_perfil"]}
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")

    @api.get("/casos")
    def casos(n: Negocio = Depends(negocio_autorizado)):
        nombres = nombres_por_cliente(n)
        return {"casos": [{**dict(c), "nombre": nombres.get(c["cliente"], "")} for c in db.filas("escalaciones", n.id)],
                "interesados": [dict(p) for p in db.filas("prospectos", n.id)]}

    @api.post("/casos/{caso_id}/resolver")
    def resolver(caso_id: int, n: Negocio = Depends(negocio_autorizado)):
        if not db.resolver_escalacion(n.id, caso_id):
            raise HTTPException(status_code=404, detail="Caso no encontrado.")
        return {"ok": True}

    app.include_router(api)

    @app.get("/panel", response_class=HTMLResponse)
    def pagina():
        return PAGINA.read_text(encoding="utf-8")
