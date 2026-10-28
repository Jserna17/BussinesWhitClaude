"""Panel del médico: indicadores, agenda sin cruces, conversaciones, casos e interesados.

Se monta en la misma app del webhook: GET /panel (página) y /panel/api/... (datos).
Acceso: cada negocio tiene su clave (`panel_clave` en el YAML o VERTICE_PANEL_CLAVE_<ID>); la página la envía
en las cabeceras X-Negocio y X-Clave.
"""

from __future__ import annotations

import hmac
import json
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import profesionales as prof_mod, transcripcion
from .agenda import Agenda, CitaNoEncontrada, Conflicto, ErrorAgenda
from .db import ESTADOS_CITA, BaseDatos
from .festivos import festivos
from .negocio import DIAS, Negocio
from .usuarios import PERMISOS, ROL_TEXTO, ROLES, Sesion, hash_token, hashear, nuevo_token, validar_clave, verificar

PAGINA = Path(__file__).with_name("panel.html")


class NuevaCita(BaseModel):
    nombre: str
    telefono: str = ""
    servicio: str
    fecha: str
    hora: str
    profesional: str = ""


class Ingreso(BaseModel):
    negocio: str
    usuario: str
    clave: str


class NuevoUsuario(BaseModel):
    usuario: str
    nombre: str
    rol: str
    profesional: str = ""
    clave: str


class ClaveNueva(BaseModel):
    clave: str


class CambioClave(BaseModel):
    actual: str
    nueva: str


class EstadoUsuario(BaseModel):
    activo: bool


class DatosProfesional(BaseModel):
    nombre: str = ""
    servicios: list[str] = []          # vacío = atiende todos los servicios
    horario: dict[str, list[list[str]]] | None = None   # None = el horario de la clínica


class MensajeEquipo(BaseModel):
    texto: str


class Reprogramacion(BaseModel):
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


VENTANA_WHATSAPP = timedelta(hours=24)  # fuera de esta ventana Meta solo permite plantillas aprobadas


def montar_panel(app: FastAPI, db: BaseDatos, negocios: dict[str, Negocio],
                 ahora: Callable[[], datetime] = datetime.now, enviar: Callable | None = None) -> None:
    api = APIRouter(prefix="/panel/api")

    fallos: dict[tuple[str, str], list[float]] = {}  # intentos de ingreso fallidos por usuario (en memoria)
    fallos_ip: dict[str, list[float]] = {}           # y por dirección de red, para frenar adivinar claves
    MAX_FALLOS, VENTANA_FALLOS, MAX_FALLOS_IP = 5, 600, 30

    def ip_de(request: Request) -> str:
        """Detrás de nuestro servidor web (Caddy, en la misma máquina) la dirección real viene en X-Forwarded-For."""
        host = request.client.host if request.client else "?"
        if host in ("127.0.0.1", "::1"):
            return request.headers.get("x-forwarded-for", "").split(",")[0].strip() or host
        return host

    def ip_bloqueada(ip: str) -> bool:
        recientes = [t for t in fallos_ip.get(ip, []) if time.monotonic() - t < VENTANA_FALLOS]
        fallos_ip[ip] = recientes
        return len(recientes) >= MAX_FALLOS_IP

    def anotar_fallo_ip(ip: str) -> None:
        fallos_ip.setdefault(ip, []).append(time.monotonic())

    def sesion_de(request: Request, x_token: str = Header(""), x_negocio: str = Header(""), x_clave: str = Header("")) -> Sesion:
        """Quién llama: una persona con su sesión (X-Token) o, para soporte, la clave de la clínica (X-Negocio + X-Clave)."""
        ip = ip_de(request)
        if ip_bloqueada(ip):
            raise HTTPException(status_code=429, detail="Demasiados intentos fallidos desde tu red. Espera 10 minutos.")
        if x_token:
            u = db.sesion_vigente(hash_token(x_token))
            if u is not None and u["negocio_id"] in negocios:
                return Sesion(negocios[u["negocio_id"]], u["id"], u["usuario"], u["nombre"], u["rol"], u["profesional"])
            anotar_fallo_ip(ip)
            raise HTTPException(status_code=401, detail="La sesión venció. Ingresa de nuevo.")
        n = negocios.get(x_negocio)
        if n is None or not n.panel_clave or not hmac.compare_digest(n.panel_clave, x_clave):
            anotar_fallo_ip(ip)
            raise HTTPException(status_code=401, detail="Clínica o clave incorrecta.")
        return Sesion(n, 0, "soporte", "Soporte Vértice", "dueno")

    def permiso(nombre: str):
        def dependencia(s: Sesion = Depends(sesion_de)) -> Sesion:
            if nombre not in s.permisos:
                raise HTTPException(status_code=403, detail="Tu usuario no tiene permiso para esto.")
            return s
        return dependencia

    def anotar(s: Sesion, accion: str, detalle: str) -> None:
        db.registrar_bitacora(s.negocio.id, s.nombre, s.rol, accion, detalle, ahora().isoformat(timespec="seconds"))

    def claves(n: Negocio) -> list[str]:
        return [n.id, f"{n.id}@openai"]

    def conversaciones_leidas(n: Negocio) -> list[dict]:
        """Conversaciones del asistente + lo que pasó fuera de su historial (equipo y pausas), con estado de pausa."""
        por_cliente: dict[str, dict] = {}
        for fila in db.conversaciones(claves(n)):
            leido = transcripcion.leer(json.loads(fila["mensajes"]))
            actual = por_cliente.get(fila["cliente"])
            if actual is None or fila["actualizado"] > actual["actualizado"]:
                por_cliente[fila["cliente"]] = {"cliente": fila["cliente"], "actualizado": fila["actualizado"], **leido}
        extras: dict[str, list] = {}
        for f in db.mensajes_chat(n.id):
            extras.setdefault(f["cliente"], []).append(f)
        for cliente, filas in extras.items():
            c = por_cliente.setdefault(cliente, {"cliente": cliente, "actualizado": filas[0]["creado"], "mensajes": [], "nombre_perfil": ""})
            c["actualizado"] = max(c["actualizado"], filas[-1]["creado"])
            for f in filas:  # cada mensaje va después del último que ya ocurrió antes que él
                nuevo = {"rol": f["rol"], "texto": f["texto"], "fecha": f["creado"][:10], "hora": f["creado"][11:16], "origen": f["origen"]}
                pos = len(c["mensajes"])
                while pos > 0 and (c["mensajes"][pos - 1].get("fecha", ""), c["mensajes"][pos - 1].get("hora", "")) > (nuevo["fecha"], nuevo["hora"]):
                    pos -= 1
                c["mensajes"].insert(pos, nuevo)
        pausas = db.pausas_vigentes(n.id)
        for cliente, c in por_cliente.items():
            c["pausada"] = cliente in pausas
            c["pausada_hasta"] = pausas[cliente]["hasta"] if cliente in pausas else ""
            ultimo = next((m for m in reversed(c["mensajes"]) if m["rol"] != "evento"), None)
            c["sin_responder"] = bool(c["pausada"] and ultimo and ultimo["rol"] == "paciente")
        return sorted(por_cliente.values(), key=lambda c: c["actualizado"], reverse=True)

    def ultimo_mensaje_paciente(n: Negocio, cliente: str) -> datetime | None:
        for c in conversaciones_leidas(n):
            if c["cliente"] == cliente:
                momentos = [datetime.fromisoformat(f'{m["fecha"]}T{m["hora"]}') for m in c["mensajes"]
                            if m["rol"] == "paciente" and m.get("fecha") and m.get("hora")]
                return max(momentos) if momentos else None
        return None

    def nombres_por_cliente(n: Negocio) -> dict[str, str]:
        nombres = {}
        for p in db.filas("prospectos", n.id):
            if p["nombre"]:
                nombres[p["cliente"]] = p["nombre"]
        for c in db.con.execute("SELECT cliente, nombre FROM citas WHERE negocio_id=? ORDER BY creado", (n.id,)):
            nombres[c["cliente"]] = c["nombre"]
        return nombres

    @api.get("/sesion")
    def sesion(s: Sesion = Depends(permiso("autenticado"))):
        n = s.negocio
        return {"negocio": n.id, "nombre": n.nombre, "asistente": n.nombre_asistente,
                "servicios": [s.nombre for s in n.servicios], "profesionales": n.nombres_profesionales(),
                "horario": {d: n.franjas(d) for d in DIAS}, "hoy": ahora().date().isoformat(),
                "horario_profesionales": {p: {d: n.franjas_de(p, d) for d in DIAS} for p in n.nombres_profesionales()},
                "abre_festivos": n.abre_festivos,
                "usuario": {"nombre": s.nombre, "rol": s.rol, "rol_texto": ROL_TEXTO[s.rol], "profesional": s.profesional,
                            "soporte": s.es_soporte},
                "permisos": sorted(s.permisos),
                "festivos": {d.isoformat(): nombre for a in (ahora().year, ahora().year + 1)
                             for d, nombre in festivos(a).items()}}

    @api.get("/resumen")
    def resumen(dias: int = 7, s: Sesion = Depends(permiso("resumen"))):
        n = s.negocio
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
    def agenda(desde: str = "", dias: int = 7, s: Sesion = Depends(permiso("agenda_ver"))):
        n = s.negocio
        inicio = date.fromisoformat(desde) if desde else ahora().date()
        fin = inicio + timedelta(days=dias)
        citas = [dict(c) for c in db.citas_entre(n.id, inicio.isoformat(), fin.isoformat())]
        bloqueos = [dict(b) for b in db.bloqueos_entre(n.id, inicio.isoformat(), fin.isoformat())]
        if s.rol == "odontologo":  # solo su propia agenda (y los bloqueos que le afectan)
            citas = [c for c in citas if c["profesional"] == s.profesional]
            bloqueos = [b for b in bloqueos if b["profesional"] in ("", s.profesional)]
        return {"desde": inicio.isoformat(), "dias": dias, "citas": citas, "bloqueos": bloqueos}

    @api.get("/solicitudes")
    def solicitudes(s: Sesion = Depends(permiso("agenda_ver"))):
        """Citas apartadas por el asistente que la recepción todavía no confirma (modo pre-reserva), las más antiguas primero."""
        n = s.negocio
        desde = ahora().isoformat(timespec="minutes")
        filas = [dict(c) for c in db.citas_entre(n.id, desde, "9999") if c["estado"] == "por_confirmar"]
        if s.rol == "odontologo":
            filas = [c for c in filas if c["profesional"] == s.profesional]
        for c in filas:
            c["espera_min"] = max(0, int((ahora() - datetime.fromisoformat(c["creado"])).total_seconds() // 60))
        return sorted(filas, key=lambda c: c["creado"])

    @api.get("/disponibilidad")
    def disponibilidad(fecha: str, servicio: str, excluir: int = 0, s: Sesion = Depends(permiso("agenda_editar"))):
        n = s.negocio
        ag = Agenda(db, n, ahora)
        try:
            libres = ag.libres(ag.fecha(fecha), ag.servicio(servicio), anticipacion_min=0, excluir_cita=excluir)
        except ErrorAgenda as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"fecha": fecha, "libres": libres}

    @api.post("/citas")
    def crear_cita(datos: NuevaCita, s: Sesion = Depends(permiso("agenda_editar"))):
        n = s.negocio
        cliente = "".join(ch for ch in datos.telefono if ch.isdigit()) or f"panel-{ahora():%Y%m%d%H%M%S}"
        try:
            cita = Agenda(db, n, ahora).reservar(cliente, datos.nombre, datos.servicio, datos.fecha, datos.hora,
                                                 datos.profesional, origen="panel", anticipacion_min=0)
            anotar(s, "cita_creada", f"{datos.nombre.strip()} · {cita['servicio']} · {cita['fecha']} {cita['hora']}"
                   f"{' · ' + cita['profesional'] if len(n.nombres_profesionales()) > 1 else ''}")
            return cita
        except Conflicto as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ErrorAgenda as e:
            raise HTTPException(status_code=400, detail=str(e))

    @api.post("/citas/{cita_id}/reprogramar")
    def reprogramar_cita(cita_id: int, datos: Reprogramacion, s: Sesion = Depends(permiso("agenda_editar"))):
        n = s.negocio
        try:
            r = Agenda(db, n, ahora).reprogramar(cita_id, datos.fecha, datos.hora, profesional=datos.profesional,
                                                 anticipacion_min=0)
            anotar(s, "cita_reprogramada", f"Cita #{cita_id} ({r['servicio']}) de {r['antes'][:16].replace('T', ' ')} a {r['fecha']} {r['hora']}")
            return r
        except CitaNoEncontrada as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Conflicto as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ErrorAgenda as e:
            raise HTTPException(status_code=400, detail=str(e))

    @api.post("/citas/{cita_id}/estado")
    def estado_cita(cita_id: int, datos: NuevoEstado, s: Sesion = Depends(permiso("estado_cita"))):
        n = s.negocio
        if datos.estado not in ESTADOS_CITA:
            raise HTTPException(status_code=400, detail="Estado inválido.")
        cita = db.cita(n.id, cita_id)
        if cita is None:
            raise HTTPException(status_code=404, detail="Cita no encontrada.")
        if s.rol == "odontologo" and (cita["profesional"] != s.profesional or datos.estado not in ("asistio", "no_asistio", "confirmada")):
            raise HTTPException(status_code=403, detail="Solo puedes marcar asistencia de tus propias citas.")
        if "agenda_editar" not in s.permisos and datos.estado == "cancelada":
            raise HTTPException(status_code=403, detail="Tu usuario no puede cancelar citas.")
        db.cambiar_estado_cita(n.id, cita_id, datos.estado)
        if cita["estado"] == "por_confirmar" and datos.estado == "confirmada":
            anotar(s, "solicitud_confirmada", f"Cita #{cita_id} ({cita['nombre']} · {cita['servicio']} · {cita['inicio'][:16].replace('T', ' ')})")
        elif cita["estado"] == "por_confirmar" and datos.estado == "cancelada":
            anotar(s, "solicitud_rechazada", f"Cita #{cita_id} ({cita['nombre']} · {cita['servicio']} · {cita['inicio'][:16].replace('T', ' ')})")
        else:
            anotar(s, "cita_estado", f"Cita #{cita_id} ({cita['nombre']}) marcada: {datos.estado}")
        return {"ok": True}

    @api.post("/bloqueos")
    def crear_bloqueo(datos: NuevoBloqueo, s: Sesion = Depends(permiso("agenda_editar"))):
        n = s.negocio
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
        anotar(s, "bloqueo_creado", f"{datos.profesional or 'Toda la clínica'} · {inicio:%Y-%m-%d %H:%M} a {fin:%Y-%m-%d %H:%M}"
               f"{' · ' + datos.motivo if datos.motivo else ''}")
        # Citas ya confirmadas dentro del bloqueo: hay que reprogramarlas (el bloqueo no las borra).
        afectadas = [dict(c) for c in db.citas_entre(n.id, inicio.isoformat(), fin.isoformat())
                     if c["estado"] in ("confirmada", "por_confirmar") and c["fin"] > inicio.isoformat()
                     and (not datos.profesional or c["profesional"] == datos.profesional)]
        return {"bloqueo_id": bid, "citas_afectadas": afectadas}

    @api.delete("/bloqueos/{bloqueo_id}")
    def borrar_bloqueo(bloqueo_id: int, s: Sesion = Depends(permiso("agenda_editar"))):
        n = s.negocio
        if not db.borrar_bloqueo(n.id, bloqueo_id):
            raise HTTPException(status_code=404, detail="Bloqueo no encontrado.")
        anotar(s, "bloqueo_quitado", f"Bloqueo #{bloqueo_id}")
        return {"ok": True}

    @api.get("/conversaciones")
    def conversaciones(s: Sesion = Depends(permiso("chats"))):
        n = s.negocio
        nombres = nombres_por_cliente(n)
        casos = {c["cliente"] for c in db.filas("escalaciones", n.id) if c["estado"] == "abierta"}
        con_cita = {c["cliente"] for c in db.citas_entre(n.id, "0000", "9999") if c["estado"] in ("confirmada", "por_confirmar")}
        lista = []
        for c in conversaciones_leidas(n):
            ultimo = next((m for m in reversed(c["mensajes"]) if m["rol"] != "evento"), None)
            lista.append({"cliente": c["cliente"], "nombre": nombres.get(c["cliente"]) or c["nombre_perfil"],
                          "actualizado": c["actualizado"], "ultimo": ultimo,
                          "mensajes": sum(1 for m in c["mensajes"] if m["rol"] == "paciente"),
                          "caso_abierto": c["cliente"] in casos, "tiene_cita": c["cliente"] in con_cita,
                          "pausada": c["pausada"], "pausada_hasta": c["pausada_hasta"], "sin_responder": c["sin_responder"]})
        return lista

    @api.get("/conversaciones/{cliente}")
    def conversacion(cliente: str, s: Sesion = Depends(permiso("chats"))):
        n = s.negocio
        for c in conversaciones_leidas(n):
            if c["cliente"] == cliente:
                aut = db.con.execute("SELECT creado FROM autorizaciones WHERE negocio_id=? AND cliente=?", (n.id, cliente)).fetchone()
                return {**c, "nombre": nombres_por_cliente(n).get(cliente) or c["nombre_perfil"], "aviso_privacidad": aut["creado"] if aut else ""}
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")

    @api.post("/conversaciones/{cliente}/tomar")
    def tomar_control(cliente: str, s: Sesion = Depends(permiso("chats"))):
        n = s.negocio
        anotar(s, "chat_tomado", f"Tomó el chat de {cliente}")
        return {"pausada_hasta": db.pausar(n.id, cliente, n.pausa_horas, "Tomada desde el panel")}

    @api.post("/conversaciones/{cliente}/devolver")
    def devolver_a_asistente(cliente: str, s: Sesion = Depends(permiso("chats"))):
        n = s.negocio
        db.reanudar(n.id, cliente)
        anotar(s, "chat_devuelto", f"Devolvió el chat de {cliente} a {n.nombre_asistente}")
        return {"ok": True}

    @api.post("/conversaciones/{cliente}/enviar")
    def responder_como_clinica(cliente: str, datos: MensajeEquipo, s: Sesion = Depends(permiso("chats"))):
        n = s.negocio
        texto = datos.texto.strip()
        if not texto:
            raise HTTPException(status_code=400, detail="Escribe un mensaje.")
        ultimo = ultimo_mensaje_paciente(n, cliente)
        if ultimo is None or ahora().replace(tzinfo=None) - ultimo > VENTANA_WHATSAPP:
            raise HTTPException(status_code=409, detail="Pasaron más de 24 horas desde el último mensaje del paciente: "
                                "WhatsApp solo permite enviar una plantilla aprobada. Llámalo o espera a que escriba.")
        enviado = False
        if enviar and n.whatsapp_phone_number_id:
            try:
                wamid = enviar(n.whatsapp_phone_number_id, cliente, texto[:4096])
            except Exception as e:  # noqa: BLE001 - el envío falló: no lo registramos como enviado
                raise HTTPException(status_code=502, detail=f"WhatsApp no aceptó el mensaje: {e}")
            if wamid:
                db.marcar_procesado(wamid)
            enviado = True
        db.guardar_mensaje_chat(n.id, cliente, "equipo", texto, "panel")
        hasta = db.pausar(n.id, cliente, n.pausa_horas, "El equipo respondió desde el panel")
        anotar(s, "mensaje_enviado", f"Escribió a {cliente} desde el panel")
        return {"ok": True, "enviado": enviado, "pausada_hasta": hasta}

    @api.get("/casos")
    def casos(s: Sesion = Depends(permiso("casos"))):
        n = s.negocio
        nombres = nombres_por_cliente(n)
        return {"casos": [{**dict(c), "nombre": nombres.get(c["cliente"], "")} for c in db.filas("escalaciones", n.id)],
                "interesados": [dict(p) for p in db.filas("prospectos", n.id)]}

    @api.post("/casos/{caso_id}/resolver")
    def resolver(caso_id: int, s: Sesion = Depends(permiso("casos"))):
        n = s.negocio
        if not db.resolver_escalacion(n.id, caso_id):
            raise HTTPException(status_code=404, detail="Caso no encontrado.")
        anotar(s, "caso_resuelto", f"Caso #{caso_id}")
        return {"ok": True}

    # --- Ingreso, usuarios e historial ---------------------------------
    @api.post("/login")
    def ingresar(datos: Ingreso, request: Request):
        ip = ip_de(request)
        if ip_bloqueada(ip):
            raise HTTPException(status_code=429, detail="Demasiados intentos fallidos desde tu red. Espera 10 minutos.")
        llave = (datos.negocio, datos.usuario.strip().lower())
        ahora_s = time.monotonic()
        recientes = [t for t in fallos.get(llave, []) if ahora_s - t < VENTANA_FALLOS]
        if len(recientes) >= MAX_FALLOS:
            raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 10 minutos e inténtalo de nuevo.")
        n = negocios.get(datos.negocio)
        u = db.usuario_por_login(datos.negocio, datos.usuario) if n else None
        # Se verifica siempre (aun si el usuario no existe) para que la respuesta tarde igual.
        valido = verificar(datos.clave, u["clave_hash"] if u else hashear("sin usuario")) and u is not None and u["activo"] == 1
        if not valido:
            fallos[llave] = recientes + [ahora_s]
            anotar_fallo_ip(ip)
            if n:
                db.registrar_bitacora(n.id, datos.usuario.strip()[:60] or "(vacío)", "-", "ingreso_fallido",
                                      "Clave o usuario incorrectos", ahora().isoformat(timespec="seconds"))
            raise HTTPException(status_code=401, detail="Usuario o clave incorrectos.")
        fallos.pop(llave, None)
        token = nuevo_token()
        db.crear_sesion(hash_token(token), u["id"])
        db.registrar_bitacora(n.id, u["nombre"], u["rol"], "ingreso", "Ingresó al panel", ahora().isoformat(timespec="seconds"))
        return {"token": token, "negocio": n.id}

    @api.post("/salir")
    def salir(x_token: str = Header("")):
        if x_token:
            db.cerrar_sesion(hash_token(x_token))
        return {"ok": True}

    @api.post("/mi-clave")
    def cambiar_mi_clave(datos: CambioClave, s: Sesion = Depends(permiso("autenticado"))):
        if s.es_soporte:
            raise HTTPException(status_code=400, detail="El acceso de soporte no tiene clave propia.")
        u = db.usuario(s.negocio.id, s.usuario_id)
        if u is None or not verificar(datos.actual, u["clave_hash"]):
            raise HTTPException(status_code=400, detail="La clave actual no es correcta.")
        motivo = validar_clave(datos.nueva)
        if motivo:
            raise HTTPException(status_code=400, detail=motivo)
        db.cambiar_clave_usuario(s.negocio.id, s.usuario_id, hashear(datos.nueva))
        anotar(s, "clave_cambiada", "Cambió su propia clave")
        return {"ok": True}

    @api.get("/usuarios")
    def listar_usuarios(s: Sesion = Depends(permiso("equipo"))):
        return [dict(u) for u in db.usuarios(s.negocio.id)]

    @api.post("/usuarios")
    def crear_usuario(datos: NuevoUsuario, s: Sesion = Depends(permiso("equipo"))):
        n = s.negocio
        login = datos.usuario.strip().lower()
        if not login.replace(".", "").replace("_", "").replace("-", "").isalnum() or len(login) < 3:
            raise HTTPException(status_code=400, detail="El usuario debe tener al menos 3 letras o números (sin espacios).")
        if not datos.nombre.strip():
            raise HTTPException(status_code=400, detail="Escribe el nombre de la persona.")
        if datos.rol not in ROLES:
            raise HTTPException(status_code=400, detail="Rol inválido.")
        if datos.rol == "odontologo" and datos.profesional not in n.nombres_profesionales():
            raise HTTPException(status_code=400, detail="Un odontólogo debe estar asociado a uno de los profesionales de la clínica.")
        motivo = validar_clave(datos.clave)
        if motivo:
            raise HTTPException(status_code=400, detail=motivo)
        try:
            uid = db.crear_usuario(n.id, login, datos.nombre, datos.rol, datos.profesional if datos.rol == "odontologo" else "",
                                   hashear(datos.clave))
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        anotar(s, "usuario_creado", f"{datos.nombre.strip()} ({login}) como {ROL_TEXTO[datos.rol]}")
        return {"id": uid}

    @api.post("/usuarios/{usuario_id}/estado")
    def estado_usuario(usuario_id: int, datos: EstadoUsuario, s: Sesion = Depends(permiso("equipo"))):
        n = s.negocio
        u = db.usuario(n.id, usuario_id)
        if u is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        if not datos.activo and u["id"] == s.usuario_id:
            raise HTTPException(status_code=400, detail="No puedes desactivar tu propio usuario.")
        if not datos.activo and u["rol"] == "dueno" and db.duenos_activos(n.id) <= 1 and not s.es_soporte:
            raise HTTPException(status_code=400, detail="Debe quedar al menos un dueño activo.")
        db.activar_usuario(n.id, usuario_id, datos.activo)
        anotar(s, "usuario_activado" if datos.activo else "usuario_desactivado", f"{u['nombre']} ({u['usuario']})")
        return {"ok": True}

    @api.post("/usuarios/{usuario_id}/clave")
    def restablecer_clave(usuario_id: int, datos: ClaveNueva, s: Sesion = Depends(permiso("equipo"))):
        u = db.usuario(s.negocio.id, usuario_id)
        if u is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        motivo = validar_clave(datos.clave)
        if motivo:
            raise HTTPException(status_code=400, detail=motivo)
        db.cambiar_clave_usuario(s.negocio.id, usuario_id, hashear(datos.clave))
        anotar(s, "clave_restablecida", f"Nueva clave para {u['nombre']} ({u['usuario']})")
        return {"ok": True}

    @api.get("/pacientes/{cliente}/datos")
    def datos_del_paciente(cliente: str, s: Sesion = Depends(permiso("datos_personales"))):
        """Derecho de acceso: todo lo que el sistema guarda de una persona."""
        n = s.negocio
        datos = db.exportar_datos_paciente(n.id, cliente)
        datos["conversaciones"] = [{"clave": c["clave"], "actualizado": c["actualizado"],
                                    "mensajes": transcripcion.leer(json.loads(c["mensajes"]))["mensajes"]} for c in datos["conversaciones"]]
        anotar(s, "datos_exportados", f"Descargó los datos de un paciente (…{cliente[-4:]})")
        return datos

    @api.delete("/pacientes/{cliente}/datos")
    def eliminar_datos_del_paciente(cliente: str, s: Sesion = Depends(permiso("datos_personales"))):
        """Derecho de supresión (a pedido del titular de los datos)."""
        if not (cliente.isdigit() or cliente.startswith("panel-")):
            raise HTTPException(status_code=400, detail="Identificador de paciente inválido.")
        resultado = db.eliminar_datos_paciente(s.negocio.id, cliente)
        anotar(s, "datos_eliminados", f"Eliminó los datos de un paciente (…{cliente[-4:]}): {resultado['conversaciones']} conversaciones, "
               f"{resultado['citas_anonimizadas']} citas anonimizadas, {resultado['citas_futuras_canceladas']} citas futuras canceladas")
        return resultado

    # --- Odontólogos de la clínica --------------------------------------
    def listar_profesionales(n: Negocio) -> list[dict]:
        out = []
        for f in db.profesionales_de(n.id):
            d = prof_mod.a_dict(f)
            out.append({"id": f["id"], "nombre": f["nombre"], "activo": bool(f["activo"]), "servicios": d.get("servicios", []),
                        "todos_los_servicios": "servicios" not in d, "horario": d.get("horario"),
                        "citas_futuras": db.citas_futuras_de(n.id, f["nombre"])})
        return out

    @api.get("/profesionales")
    def profesionales_de_la_clinica(s: Sesion = Depends(permiso("equipo"))):
        return {"profesionales": listar_profesionales(s.negocio), "servicios": [x.nombre for x in s.negocio.servicios]}

    def datos_validos(datos: DatosProfesional, n: Negocio) -> tuple[list[str], dict | None]:
        try:
            return prof_mod.validar_servicios(datos.servicios, n), prof_mod.validar_horario(datos.horario)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @api.post("/profesionales")
    def crear_profesional(datos: DatosProfesional, s: Sesion = Depends(permiso("equipo"))):
        n = s.negocio
        try:
            nombre = prof_mod.validar_nombre(datos.nombre)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        servicios, horario = datos_validos(datos, n)
        sj, hj = prof_mod.como_json(servicios, horario)
        try:
            pid = db.crear_profesional(n.id, nombre, sj, hj)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        movidas = 0
        if not any(f["activo"] for f in db.profesionales_de(n.id) if f["id"] != pid):  # el primero de una clínica de un solo consultorio
            movidas = db.pasar_citas_de_consultorio(n.id, nombre)
        prof_mod.aplicar(db, negocios, n.id)
        anotar(s, "profesional_creado", f"{nombre} ({'todos los servicios' if not servicios else ', '.join(servicios)})"
               f"{f'; {movidas} citas del consultorio pasaron a él' if movidas else ''}")
        return {"id": pid, "citas_movidas": movidas}

    @api.put("/profesionales/{profesional_id}")
    def editar_profesional(profesional_id: int, datos: DatosProfesional, s: Sesion = Depends(permiso("equipo"))):
        n = s.negocio
        f = db.profesional(n.id, profesional_id)
        if f is None:
            raise HTTPException(status_code=404, detail="Odontólogo no encontrado.")
        servicios, horario = datos_validos(datos, n)   # el nombre no se cambia: las citas y los usuarios están ligados a él
        sj, hj = prof_mod.como_json(servicios, horario)
        db.actualizar_profesional(n.id, profesional_id, sj, hj)
        prof_mod.aplicar(db, negocios, n.id)
        anotar(s, "profesional_editado", f"{f['nombre']}: {'todos los servicios' if not servicios else ', '.join(servicios)}"
               f"{' · horario propio' if horario else ' · horario de la clínica'}")
        return {"ok": True, "citas_futuras": db.citas_futuras_de(n.id, f["nombre"])}

    @api.post("/profesionales/{profesional_id}/estado")
    def estado_profesional(profesional_id: int, datos: EstadoUsuario, s: Sesion = Depends(permiso("equipo"))):
        n = s.negocio
        f = db.profesional(n.id, profesional_id)
        if f is None:
            raise HTTPException(status_code=404, detail="Odontólogo no encontrado.")
        if not datos.activo and f["activo"] and sum(1 for x in db.profesionales_de(n.id) if x["activo"]) <= 1:
            raise HTTPException(status_code=400, detail="Debe quedar al menos un odontólogo activo.")
        db.activar_profesional(n.id, profesional_id, datos.activo)
        prof_mod.aplicar(db, negocios, n.id)
        futuras = db.citas_futuras_de(n.id, f["nombre"])
        anotar(s, "profesional_activado" if datos.activo else "profesional_desactivado",
               f"{f['nombre']}{f'; tiene {futuras} citas futuras por reprogramar' if futuras and not datos.activo else ''}")
        return {"ok": True, "citas_futuras": futuras}

    @api.get("/bitacora")
    def historial(dias: int = 7, limite: int = 300, s: Sesion = Depends(permiso("historial"))):
        desde = (ahora() - timedelta(days=max(1, min(dias, 90)))).isoformat(timespec="seconds")
        return [dict(f) for f in db.bitacora(s.negocio.id, desde, max(1, min(limite, 1000)))]

    app.include_router(api)

    @app.get("/panel", response_class=HTMLResponse)
    def pagina():
        return PAGINA.read_text(encoding="utf-8")
