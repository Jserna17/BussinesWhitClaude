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
from .negocio import cargar_negocios

RAIZ = Path(__file__).resolve().parent.parent


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
    print("Datos de ejemplo agregados a", ruta)


if __name__ == "__main__":
    sembrar(sys.argv[1] if len(sys.argv) > 1 else str(RAIZ / "demo.db"))
