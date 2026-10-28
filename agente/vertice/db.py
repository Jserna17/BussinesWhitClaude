"""Persistencia en SQLite: conversaciones, citas, bloqueos de agenda, prospectos y casos para humanos."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

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
CREATE INDEX IF NOT EXISTS citas_negocio_inicio ON citas (negocio_id, inicio);
CREATE TABLE IF NOT EXISTS bloqueos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id TEXT NOT NULL,
    profesional TEXT NOT NULL DEFAULT '',   -- '' = bloquea a todos
    inicio TEXT NOT NULL,
    fin TEXT NOT NULL,
    motivo TEXT NOT NULL DEFAULT '',
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
CREATE TABLE IF NOT EXISTS pausas (
    negocio_id TEXT NOT NULL,
    cliente TEXT NOT NULL,
    hasta TEXT NOT NULL,
    motivo TEXT NOT NULL,
    creado TEXT NOT NULL,
    PRIMARY KEY (negocio_id, cliente)
);
CREATE TABLE IF NOT EXISTS mensajes_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id TEXT NOT NULL,
    cliente TEXT NOT NULL,
    rol TEXT NOT NULL,
    texto TEXT NOT NULL,
    origen TEXT NOT NULL,
    creado TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mensajes_chat ON mensajes_chat (negocio_id, cliente, creado);
"""

ZONA = ZoneInfo("America/Bogota")

# Columnas agregadas después de la v0.1 (las bases existentes se actualizan solas).
MIGRACIONES = {
    "citas": {"profesional": "TEXT NOT NULL DEFAULT 'Consultorio'", "origen": "TEXT NOT NULL DEFAULT 'asistente'"},
    "escalaciones": {"estado": "TEXT NOT NULL DEFAULT 'abierta'"},
}

# Estados que ocupan la silla. "cancelada" la libera.
ESTADOS_OCUPAN = ("confirmada", "asistio", "no_asistio")
ESTADOS_CITA = ESTADOS_OCUPAN + ("cancelada",)


class CitaNoEncontrada(Exception):
    """La cita no existe, no es de este paciente o ya no está confirmada."""


class Conflicto(Exception):
    """El horario ya no está libre (otro paciente lo tomó o hay un bloqueo)."""


class _Resultado:
    """Filas ya leídas de un cursor (se leen dentro del candado para no cruzar hilos)."""

    def __init__(self, cur: sqlite3.Cursor):
        self.filas = cur.fetchall()
        self.lastrowid, self.rowcount = cur.lastrowid, cur.rowcount

    def fetchall(self) -> list[sqlite3.Row]:
        return self.filas

    def fetchone(self) -> sqlite3.Row | None:
        return self.filas[0] if self.filas else None

    def __iter__(self):
        return iter(self.filas)


class _Conexion:
    """Conexión compartida entre hilos (FastAPI atiende el panel en paralelo): cada consulta toma el candado."""

    def __init__(self, con: sqlite3.Connection, lock: threading.RLock):
        self._con, self._lock = con, lock

    def execute(self, sql: str, params: tuple = ()) -> _Resultado:
        with self._lock:
            return _Resultado(self._con.execute(sql, params))

    def executescript(self, sql: str) -> None:
        with self._lock:
            self._con.executescript(sql)


class BaseDatos:
    def __init__(self, ruta: Path | str):
        self._lock = threading.RLock()
        # isolation_level=None: las transacciones se abren a mano con BEGIN IMMEDIATE.
        con = sqlite3.connect(str(ruta), check_same_thread=False, isolation_level=None, timeout=15)
        con.row_factory = sqlite3.Row
        self.con = _Conexion(con, self._lock)
        if str(ruta) != ":memory:":
            self.con.execute("PRAGMA journal_mode=WAL")
        self.con.executescript(ESQUEMA)
        self._migrar()

    def _migrar(self) -> None:
        for tabla, columnas in MIGRACIONES.items():
            existentes = {f["name"] for f in self.con.execute(f"PRAGMA table_info({tabla})")}
            for col, tipo in columnas.items():
                if col not in existentes:
                    self.con.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")

    def _ahora(self) -> str:
        # Las clínicas están en Colombia: todo se registra en hora de Bogotá, sea cual sea el servidor.
        return datetime.now(ZONA).replace(tzinfo=None).isoformat(timespec="seconds")

    @contextmanager
    def transaccion(self):
        """Transacción de escritura exclusiva: nadie más (ni otro proceso) escribe hasta terminar."""
        with self._lock:
            self.con.execute("BEGIN IMMEDIATE")
            try:
                yield self.con
            except BaseException:
                self.con.execute("ROLLBACK")
                raise
            else:
                self.con.execute("COMMIT")

    def _escribir(self, sql: str, params: tuple) -> _Resultado:
        with self.transaccion() as con:
            return con.execute(sql, params)

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
        self._escribir(
            "INSERT INTO conversaciones VALUES (?,?,?,?) "
            "ON CONFLICT(negocio_id, cliente) DO UPDATE SET mensajes=excluded.mensajes, "
            "actualizado=excluded.actualizado",
            (negocio_id, cliente, json.dumps(mensajes, ensure_ascii=False),
             momento.isoformat(timespec="seconds")),
        )

    def conversaciones(self, claves: list[str]) -> list[sqlite3.Row]:
        marcas = ",".join("?" * len(claves))
        return self.con.execute(
            f"SELECT * FROM conversaciones WHERE negocio_id IN ({marcas}) ORDER BY actualizado DESC", claves
        ).fetchall()

    # --- Citas y bloqueos ----------------------------------------------
    def ocupaciones(self, negocio_id: str, desde: str, hasta: str, con=None, excluir_cita: int = 0) -> list[dict]:
        """Citas que ocupan silla y bloqueos que se cruzan con [desde, hasta). `excluir_cita`: una cita que se está moviendo."""
        con = con or self.con
        estados = ",".join("?" * len(ESTADOS_OCUPAN))
        citas = con.execute(
            f"SELECT profesional, inicio, fin FROM citas WHERE negocio_id=? AND estado IN ({estados}) "
            "AND inicio < ? AND fin > ? AND id != ?",
            (negocio_id, *ESTADOS_OCUPAN, hasta, desde, excluir_cita),
        ).fetchall()
        bloqueos = con.execute(
            "SELECT profesional, inicio, fin FROM bloqueos WHERE negocio_id=? AND inicio < ? AND fin > ?",
            (negocio_id, hasta, desde),
        ).fetchall()
        return [dict(r) for r in citas] + [dict(r) for r in bloqueos]

    def reservar(self, negocio_id: str, candidatos: list[str], cliente: str, nombre: str, servicio: str,
                 inicio: str, fin: str, origen: str) -> tuple[int, str]:
        """Crea la cita con el primer profesional libre. Revisa y escribe en la misma transacción
        exclusiva, así dos pacientes simultáneos nunca reciben la misma silla."""
        with self.transaccion() as con:
            ocupados = self.ocupaciones(negocio_id, inicio, fin, con)
            todos_bloqueados = any(o["profesional"] == "" for o in ocupados)
            for prof in candidatos:
                if todos_bloqueados or any(o["profesional"] == prof for o in ocupados):
                    continue
                cur = con.execute(
                    "INSERT INTO citas (negocio_id, cliente, nombre, servicio, inicio, fin, creado, profesional, origen) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (negocio_id, cliente, nombre, servicio, inicio, fin, self._ahora(), prof, origen),
                )
                return cur.lastrowid, prof
        raise Conflicto("Ese horario ya no está disponible.")

    def cita(self, negocio_id: str, cita_id: int) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM citas WHERE id=? AND negocio_id=?", (cita_id, negocio_id)).fetchone()

    def reprogramar(self, negocio_id: str, cita_id: int, candidatos: list[str], inicio: str, fin: str,
                    cliente: str | None = None) -> str:
        """Mueve una cita confirmada a otro horario en una sola transacción: el horario viejo se libera y el nuevo se
        ocupa sin que otro paciente pueda colarse entre medio. Devuelve el profesional."""
        with self.transaccion() as con:
            cita = con.execute("SELECT * FROM citas WHERE id=? AND negocio_id=? AND estado='confirmada'",
                               (cita_id, negocio_id)).fetchone()
            if cita is None or (cliente is not None and cita["cliente"] != cliente):
                raise CitaNoEncontrada("No encontré una cita confirmada con ese id.")
            ocupados = self.ocupaciones(negocio_id, inicio, fin, con, excluir_cita=cita_id)
            if not any(o["profesional"] == "" for o in ocupados):
                for prof in candidatos:
                    if any(o["profesional"] == prof for o in ocupados):
                        continue
                    con.execute("UPDATE citas SET inicio=?, fin=?, profesional=? WHERE id=?", (inicio, fin, prof, cita_id))
                    return prof
        raise Conflicto("Ese horario ya no está disponible.")

    def citas_entre(self, negocio_id: str, desde: str, hasta: str) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM citas WHERE negocio_id=? AND inicio >= ? AND inicio < ? ORDER BY inicio",
            (negocio_id, desde, hasta),
        ).fetchall()

    def citas_de_cliente(self, negocio_id: str, cliente: str, desde: str | None = None) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM citas WHERE negocio_id=? AND cliente=? AND estado='confirmada' "
            "AND inicio >= ? ORDER BY inicio",
            (negocio_id, cliente, desde or self._ahora()),
        ).fetchall()

    def cancelar_cita(self, negocio_id: str, cliente: str, cita_id: int) -> bool:
        cur = self._escribir(
            "UPDATE citas SET estado='cancelada' WHERE id=? AND negocio_id=? AND cliente=? "
            "AND estado='confirmada'",
            (cita_id, negocio_id, cliente),
        )
        return cur.rowcount == 1

    def cambiar_estado_cita(self, negocio_id: str, cita_id: int, estado: str) -> bool:
        if estado not in ESTADOS_CITA:
            raise ValueError(f"Estado inválido: {estado}")
        cur = self._escribir("UPDATE citas SET estado=? WHERE id=? AND negocio_id=?", (estado, cita_id, negocio_id))
        return cur.rowcount == 1

    def crear_bloqueo(self, negocio_id: str, profesional: str, inicio: str, fin: str, motivo: str) -> int:
        cur = self._escribir(
            "INSERT INTO bloqueos (negocio_id, profesional, inicio, fin, motivo, creado) VALUES (?,?,?,?,?,?)",
            (negocio_id, profesional, inicio, fin, motivo, self._ahora()),
        )
        return cur.lastrowid

    def borrar_bloqueo(self, negocio_id: str, bloqueo_id: int) -> bool:
        return self._escribir("DELETE FROM bloqueos WHERE id=? AND negocio_id=?", (bloqueo_id, negocio_id)).rowcount == 1

    def bloqueos_entre(self, negocio_id: str, desde: str, hasta: str) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM bloqueos WHERE negocio_id=? AND inicio < ? AND fin > ? ORDER BY inicio",
            (negocio_id, hasta, desde),
        ).fetchall()

    # --- Prospectos y escalaciones -------------------------------------
    def registrar_prospecto(self, negocio_id, cliente, nombre, interes, notas) -> int:
        return self._escribir(
            "INSERT INTO prospectos (negocio_id, cliente, nombre, interes, notas, creado) VALUES (?,?,?,?,?,?)",
            (negocio_id, cliente, nombre, interes, notas, self._ahora()),
        ).lastrowid

    def registrar_escalacion(self, negocio_id, cliente, motivo) -> int:
        return self._escribir(
            "INSERT INTO escalaciones (negocio_id, cliente, motivo, creado) VALUES (?,?,?,?)",
            (negocio_id, cliente, motivo, self._ahora()),
        ).lastrowid

    def resolver_escalacion(self, negocio_id: str, caso_id: int) -> bool:
        return self._escribir(
            "UPDATE escalaciones SET estado='resuelta' WHERE id=? AND negocio_id=?", (caso_id, negocio_id)
        ).rowcount == 1

    def filas(self, tabla: str, negocio_id: str, desde: str = "") -> list[sqlite3.Row]:
        assert tabla in {"prospectos", "escalaciones"}
        return self.con.execute(
            f"SELECT * FROM {tabla} WHERE negocio_id=? AND creado >= ? ORDER BY creado DESC", (negocio_id, desde)
        ).fetchall()

    # --- Pausa del asistente y mensajes fuera de su historial ----------
    def pausar(self, negocio_id: str, cliente: str, horas: float, motivo: str) -> str:
        """El asistente se calla en este chat hasta `hasta` (hora de Bogotá). Devuelve ese instante."""
        ahora = datetime.fromisoformat(self._ahora())
        hasta = (ahora + timedelta(hours=horas)).isoformat(timespec="seconds")
        self._escribir("INSERT OR REPLACE INTO pausas (negocio_id, cliente, hasta, motivo, creado) VALUES (?,?,?,?,?)",
                       (negocio_id, cliente, hasta, motivo, ahora.isoformat(timespec="seconds")))
        return hasta

    def reanudar(self, negocio_id: str, cliente: str) -> bool:
        return self._escribir("DELETE FROM pausas WHERE negocio_id=? AND cliente=?", (negocio_id, cliente)).rowcount == 1

    def pausa_vigente(self, negocio_id: str, cliente: str) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM pausas WHERE negocio_id=? AND cliente=? AND hasta > ?",
                                (negocio_id, cliente, self._ahora())).fetchone()

    def pausas_vigentes(self, negocio_id: str) -> dict[str, sqlite3.Row]:
        filas = self.con.execute("SELECT * FROM pausas WHERE negocio_id=? AND hasta > ?",
                                 (negocio_id, self._ahora())).fetchall()
        return {f["cliente"]: f for f in filas}

    def guardar_mensaje_chat(self, negocio_id: str, cliente: str, rol: str, texto: str, origen: str) -> int:
        """rol: 'paciente' (escrito mientras el asistente estaba en pausa) o 'equipo' (persona de la clínica)."""
        return self._escribir(
            "INSERT INTO mensajes_chat (negocio_id, cliente, rol, texto, origen, creado) VALUES (?,?,?,?,?,?)",
            (negocio_id, cliente, rol, texto, origen, self._ahora())).lastrowid

    def mensajes_chat(self, negocio_id: str, cliente: str | None = None, desde: str = "") -> list[sqlite3.Row]:
        if cliente is None:
            return self.con.execute("SELECT * FROM mensajes_chat WHERE negocio_id=? AND creado >= ? ORDER BY id",
                                    (negocio_id, desde)).fetchall()
        return self.con.execute("SELECT * FROM mensajes_chat WHERE negocio_id=? AND cliente=? AND creado >= ? ORDER BY id",
                                (negocio_id, cliente, desde)).fetchall()

    # --- Idempotencia del webhook (Meta reintenta entregas) -------------
    def marcar_procesado(self, mensaje_id: str) -> bool:
        """Devuelve False si el mensaje ya se había procesado."""
        cur = self._escribir("INSERT OR IGNORE INTO mensajes_procesados (id) VALUES (?)", (mensaje_id,))
        return cur.rowcount == 1
