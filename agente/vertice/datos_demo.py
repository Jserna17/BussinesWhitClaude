"""Agrega citas y bloqueos de EJEMPLO a una base de demostración, para mostrar el panel en visitas.

Uso:  python -m vertice.datos_demo demo.db
Las conversaciones salen de la batería en vivo (python -m vertice.pruebas_vivo --db demo.db).
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from .agenda import Agenda, Conflicto
from .agente import ahora_bogota
from .db import BaseDatos
from .festivos import festivo
from .negocio import cargar_negocios
from .usuarios import hashear

RAIZ = Path(__file__).resolve().parent.parent


CLAVE_DEMO = "Demo12345"  # la de todas las personas de ejemplo
EQUIPO_DEMO = [("direccion", "Dr. Juan Pérez", "dueno", ""), ("marta", "Marta Gil", "recepcion", ""),
               ("laura", "Dra. Laura Gómez", "odontologo", "Dra. Laura Gómez"),
               ("andres", "Dr. Andrés Ríos", "odontologo", "Dr. Andrés Ríos")]


def sembrar_equipo(db: BaseDatos, negocio_id: str = "clinica-demo") -> None:
    """Personas con acceso al panel (una por rol) y un historial de cambios de ejemplo."""
    for usuario, nombre, rol, prof in EQUIPO_DEMO:
        if db.usuario_por_login(negocio_id, usuario) is None:
            db.crear_usuario(negocio_id, usuario, nombre, rol, prof, hashear(CLAVE_DEMO))
    if db.con.execute("SELECT COUNT(*) AS n FROM bitacora WHERE negocio_id=? AND quien='Marta Gil'", (negocio_id,)).fetchone()["n"]:
        return
    ahora = ahora_bogota().replace(tzinfo=None)

    def hace(horas: float) -> str:
        return (ahora - timedelta(hours=horas)).isoformat(timespec="seconds")
    for horas, quien, rol, accion, detalle in [
        (30, "Marta Gil", "recepcion", "ingreso", "Ingresó al panel"),
        (29.5, "Marta Gil", "recepcion", "cita_creada", "Marta R. · Limpieza dental (profilaxis) · cita por teléfono"),
        (26, "Sofía", "asistente", "cita_creada", "Carolina Restrepo · Limpieza dental (profilaxis) · agendada por WhatsApp"),
        (25, "Marta Gil", "recepcion", "cita_reprogramada", "Jorge P. · Resina estética: movida a otro día a pedido del paciente"),
        (24, "Dr. Juan Pérez", "dueno", "bloqueo_creado", "Dr. Andrés Ríos · congreso (tarde del viernes)"),
        (23, "Marta Gil", "recepcion", "chat_tomado", "Tomó el chat de un paciente con una consulta de precios"),
        (22.8, "Marta Gil", "recepcion", "mensaje_enviado", "Respondió al paciente desde el panel"),
        (22.6, "Marta Gil", "recepcion", "chat_devuelto", "Devolvió el chat a Sofía"),
        (9, "Dra. Laura Gómez", "odontologo", "cita_estado", "Paciente de las 8:00 marcado: asistió"),
        (8.5, "Dr. Andrés Ríos", "odontologo", "cita_estado", "Paciente de las 10:00 marcado: no asistió"),
        (3, "Dr. Juan Pérez", "dueno", "usuario_creado", "Agregó a Marta Gil como Recepción"),
    ]:
        db.registrar_bitacora(negocio_id, quien, rol, accion, detalle, hace(horas))


def sembrar_solicitudes(db: BaseDatos, negocio_id: str = "clinica-demo") -> None:
    """Dos solicitudes de ejemplo "por confirmar" (así se ve el modo pre-reserva, para clínicas con agenda en otro sistema)."""
    from dataclasses import replace
    n = replace(cargar_negocios(RAIZ / "negocios")[negocio_id], modo_agenda="pre_reserva")
    ag = Agenda(db, n, ahora_bogota)
    hoy = ahora_bogota().date()
    ahora = ahora_bogota().replace(tzinfo=None)
    for i, (nombre, servicio, dias, hora, minutos) in enumerate([
        ("Paciente ejemplo · Valentina R.", "Valoración odontológica", 2, "10:00", 25),
        ("Paciente ejemplo · Camilo A.", "Limpieza dental (profilaxis)", 3, "09:00", 190),
    ]):
        if db.con.execute("SELECT 1 FROM citas WHERE negocio_id=? AND nombre=?", (negocio_id, nombre)).fetchone():
            continue
        d = hoy + timedelta(days=dias)
        while d.weekday() == 6 or festivo(d):
            d += timedelta(days=1)
        try:
            cita = ag.reservar(f"57300000009{i}", nombre, servicio, d.isoformat(), hora, origen="asistente", anticipacion_min=0)
        except Conflicto:
            continue
        db.con.execute("UPDATE citas SET creado=? WHERE id=?", ((ahora - timedelta(minutes=minutos)).isoformat(timespec="seconds"), cita["cita_id"]))


def sembrar(ruta: str, negocio_id: str = "clinica-demo") -> None:
    db = BaseDatos(ruta)
    n = cargar_negocios(RAIZ / "negocios")[negocio_id]
    ag = Agenda(db, n, ahora_bogota)
    hoy = ahora_bogota().date()

    def dia_habil(desde: int) -> str:
        d = hoy + timedelta(days=desde)
        while d.weekday() == 6:
            d += timedelta(days=1)
        return d.isoformat()

    # Citas tomadas por recepción en los próximos días (nombres de ejemplo)
    for i, (nombre, servicio, dias, hora) in enumerate([
        ("Paciente ejemplo · Marta R.", "Limpieza dental (profilaxis)", 1, "08:00"),
        ("Paciente ejemplo · Jorge P.", "Resina estética", 1, "15:00"),
        ("Paciente ejemplo · Sara L.", "Valoración de ortodoncia", 2, "09:30"),
        ("Paciente ejemplo · Diego M.", "Ortodoncia (control)", 3, "16:00"),
        ("Paciente ejemplo · Lucía V.", "Valoración odontológica", 4, "10:00"),
    ]):
        try:
            ag.reservar(f"ejemplo{i}", nombre, servicio, dia_habil(dias), hora, origen="panel", anticipacion_min=0)
        except Conflicto:
            pass

    # Un bloqueo: el Dr. Andrés en congreso una tarde
    viernes = hoy + timedelta(days=(4 - hoy.weekday()) % 7 or 7)
    db.crear_bloqueo(n.id, "Dr. Andrés Ríos", f"{viernes}T14:00:00", f"{viernes}T18:00:00", "Congreso (ejemplo)")

    # Citas pasadas ya marcadas, para el indicador de inasistencia
    pasados = [("asistio", 1, "Andrea M."), ("asistio", 2, "Felipe G."), ("no_asistio", 2, "Diana C."), ("asistio", 3, "Mateo V.")]
    for i, (estado, dias, quien) in enumerate(pasados):
        d = hoy - timedelta(days=dias)
        if d.weekday() == 6:
            continue
        inicio = datetime.combine(d, datetime.strptime(f"{8 + i}:00", "%H:%M").time())
        cid, _ = db.reservar(n.id, ["Dra. Laura Gómez"], f"pasado{i}", f"Paciente ejemplo · {quien}",
                             "Valoración odontológica", inicio.isoformat(), (inicio + timedelta(minutes=30)).isoformat(), "panel")
        db.cambiar_estado_cita(n.id, cid, estado)
    # Respuestas de ejemplo a los recordatorios: una confirma y otra pide cambiar
    for fila in db.con.execute("SELECT id, cliente, nombre FROM citas WHERE negocio_id=? AND cliente LIKE 'ejemplo%' ORDER BY inicio", (n.id,)):
        if "Marta" in fila["nombre"]:
            db.marcar_confirmacion(n.id, fila["id"], fila["cliente"], "confirmo")
        if "Jorge" in fila["nombre"]:
            db.marcar_confirmacion(n.id, fila["id"], fila["cliente"], "cambiar")
    sembrar_equipo(db, negocio_id)
    sembrar_solicitudes(db, negocio_id)
    print("Datos de ejemplo agregados a", ruta)


if __name__ == "__main__":
    sembrar(sys.argv[1] if len(sys.argv) > 1 else str(RAIZ / "demo.db"))
