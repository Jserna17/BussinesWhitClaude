"""Persistencia en SQLite: conversaciones, citas, prospectos y casos para humanos."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS conversaciones (
    negocio_id TEXT NOT NULL,
    cliente TEXT NOT NULL,
    mensajes TEXT NOT NULL,
    actualizado TEXT NOT NULL,
    PRIMARY KEY (negocio_id, cliente)
);
CREATE TABLE IF NOT EXISTS citas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id TEXT NOT NULL,
    cliente TEXT NOT NULL,
    nombre TEXT NOT NULL,
    servicio TEXT NOT NULL,
    inicio TEXT NOT NULL,
    fin TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'confirmada',
    creado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prospectos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id TEXT NOT NULL,
    cliente TEXT NOT NULL,
    nombre TEXT,
    interes TEXT NOT NULL,
    notas TEXT,
    creado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS escalaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id TEXT NOT NULL,
    cliente TEXT NOT NULL,
    motivo TEXT NOT NULL,
    creado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mensajes_procesados (
    id TEXT PRIMARY KEY
);
"""


class BaseDatos:
    def __init__(self, ruta: Path | str):
        self._lock = threading.Lock()
        self.con = sqlite3.connect(str(ruta), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)

    def _ahora(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    # --- Conversaciones -------------------------------------------------
    def historial(self, negocio_id: str, cliente: str) -> list[dict]:
        fila = self.con.execute(
            "SELECT mensajes FROM conversaciones WHERE negocio_id=? AND cliente=?",
            (negocio_id, cliente),
        ).fetchone()
        return json.loads(fila["mensajes"]) if fila else []

    def ultima_actividad(self, negocio_id: str, cliente: str) -> datetime | None:
        fila = self.con.execute(
            "SELECT actualizado FROM conversaciones WHERE negocio_id=? AND cliente=?",
            (negocio_id, cliente),
        ).fetchone()
        return datetime.fromisoformat(fila["actualizado"]) if fila else None

    def guardar_historial(
        self, negocio_id: str, cliente: str, mensajes: list[dict], momento: datetime
    ) -> None:
        with self._lock, self.con:
            self.con.execute(
                "INSERT INTO conversaciones VALUES (?,?,?,?) "
                "ON CONFLICT(negocio_id, cliente) DO UPDATE SET mensajes=excluded.mensajes, "
                "actualizado=excluded.actualizado",
                (negocio_id, cliente, json.dumps(mensajes, ensure_ascii=False),
                 momento.isoformat(timespec="seconds")),
            )

    # --- Citas ----------------------------------------------------------
    def citas_del_dia(self, negocio_id: str, fecha: str) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM citas WHERE negocio_id=? AND estado='confirmada' AND inicio LIKE ? "
            "ORDER BY inicio",
            (negocio_id, f"{fecha}%"),
        ).fetchall()

    def citas_de_cliente(self, negocio_id: str, cliente: str) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM citas WHERE negocio_id=? AND cliente=? AND estado='confirmada' "
            "AND inicio >= ? ORDER BY inicio",
            (negocio_id, cliente, self._ahora()),
        ).fetchall()

    def crear_cita(self, negocio_id, cliente, nombre, servicio, inicio, fin) -> int:
        with self._lock, self.con:
            cur = self.con.execute(
                "INSERT INTO citas (negocio_id, cliente, nombre, servicio, inicio, fin, creado) "
                "VALUES (?,?,?,?,?,?,?)",
                (negocio_id, cliente, nombre, servicio, inicio, fin, self._ahora()),
            )
            return cur.lastrowid

    def cancelar_cita(self, negocio_id: str, cliente: str, cita_id: int) -> bool:
        with self._lock, self.con:
            cur = self.con.execute(
                "UPDATE citas SET estado='cancelada' WHERE id=? AND negocio_id=? AND cliente=? "
                "AND estado='confirmada'",
                (cita_id, negocio_id, cliente),
            )
            return cur.rowcount == 1

    # --- Prospectos y escalaciones -------------------------------------
    def registrar_prospecto(self, negocio_id, cliente, nombre, interes, notas) -> int:
        with self._lock, self.con:
            cur = self.con.execute(
                "INSERT INTO prospectos (negocio_id, cliente, nombre, interes, notas, creado) "
                "VALUES (?,?,?,?,?,?)",
                (negocio_id, cliente, nombre, interes, notas, self._ahora()),
            )
            return cur.lastrowid

    def registrar_escalacion(self, negocio_id, cliente, motivo) -> int:
        with self._lock, self.con:
            cur = self.con.execute(
                "INSERT INTO escalaciones (negocio_id, cliente, motivo, creado) VALUES (?,?,?,?)",
                (negocio_id, cliente, motivo, self._ahora()),
            )
            return cur.lastrowid

    # --- Idempotencia del webhook (Meta reintenta entregas) -------------
    def marcar_procesado(self, mensaje_id: str) -> bool:
        """Devuelve False si el mensaje ya se había procesado."""
        with self._lock, self.con:
            cur = self.con.execute(
                "INSERT OR IGNORE INTO mensajes_procesados (id) VALUES (?)", (mensaje_id,)
            )
            return cur.rowcount == 1
