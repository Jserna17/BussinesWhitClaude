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
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id TEXT NOT NULL,
    usuario TEXT NOT NULL,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL,
    profesional TEXT NOT NULL DEFAULT '',
    clave_hash TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1,
    creado TEXT NOT NULL,
    UNIQUE (negocio_id, usuario)
);
CREATE TABLE IF NOT EXISTS sesiones (
    token_hash TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    expira TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bitacora (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id TEXT NOT NULL,
    quien TEXT NOT NULL,
    rol TEXT NOT NULL,
    accion TEXT NOT NULL,
    detalle TEXT NOT NULL,
    creado TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bitacora ON bitacora (negocio_id, creado);
CREATE TABLE IF NOT EXISTS estado (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    actualizado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fallos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negocio_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    detalle TEXT NOT NULL,
    creado TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fallos ON fallos (tipo, creado);
CREATE TABLE IF NOT EXISTS autorizaciones (
    negocio_id TEXT NOT NULL,
    cliente TEXT NOT NULL,
    version TEXT NOT NULL,
    creado TEXT NOT NULL,
    PRIMARY KEY (negocio_id, cliente)
);
"""

ZONA = ZoneInfo("America/Bogota")

# Columnas agregadas después de la v0.1 (las bases existentes se actualizan solas).
MIGRACIONES = {
    "citas": {"profesional": "TEXT NOT NULL DEFAULT 'Consultorio'", "origen": "TEXT NOT NULL DEFAULT 'asistente'",
              "recordatorio_1": "TEXT NOT NULL DEFAULT ''", "recordatorio_2": "TEXT NOT NULL DEFAULT ''",
              "confirmacion": "TEXT NOT NULL DEFAULT ''"},
    "escalaciones": {"estado": "TEXT NOT NULL DEFAULT 'abierta'"},
}

# Estados que ocupan la silla. "cancelada" la libera.
# "por_confirmar": la clínica lleva su agenda en otro sistema; Sofía aparta el horario y la recepción lo confirma.
ESTADOS_OCUPAN = ("por_confirmar", "confirmada", "asistio", "no_asistio")
ESTADOS_CITA = ESTADOS_OCUPAN + ("cancelada",)
ESTADOS_ACTIVOS = ("por_confirmar", "confirmada")  # citas futuras que el paciente puede ver, mover o cancelar
_ACTIVOS_SQL = "estado IN ('por_confirmar','confirmada')"


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
                 inicio: str, fin: str, origen: str, estado: str = "confirmada") -> tuple[int, str]:
        """Crea la cita con el primer profesional libre. Revisa y escribe en la misma transacción
        exclusiva, así dos pacientes simultáneos nunca reciben la misma silla."""
        with self.transaccion() as con:
            ocupados = self.ocupaciones(negocio_id, inicio, fin, con)
            todos_bloqueados = any(o["profesional"] == "" for o in ocupados)
            for prof in candidatos:
                if todos_bloqueados or any(o["profesional"] == prof for o in ocupados):
                    continue
                cur = con.execute(
                    "INSERT INTO citas (negocio_id, cliente, nombre, servicio, inicio, fin, creado, profesional, origen, estado) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (negocio_id, cliente, nombre, servicio, inicio, fin, self._ahora(), prof, origen, estado),
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
            cita = con.execute(f"SELECT * FROM citas WHERE id=? AND negocio_id=? AND {_ACTIVOS_SQL}",
                               (cita_id, negocio_id)).fetchone()
            if cita is None or (cliente is not None and cita["cliente"] != cliente):
                raise CitaNoEncontrada("No encontré una cita vigente con ese id.")
            ocupados = self.ocupaciones(negocio_id, inicio, fin, con, excluir_cita=cita_id)
            if not any(o["profesional"] == "" for o in ocupados):
                for prof in candidatos:
                    if any(o["profesional"] == prof for o in ocupados):
                        continue
                    con.execute("UPDATE citas SET inicio=?, fin=?, profesional=?, recordatorio_1='', recordatorio_2='', confirmacion='' "
                                "WHERE id=?", (inicio, fin, prof, cita_id))
                    return prof
        raise Conflicto("Ese horario ya no está disponible.")

    # --- Recordatorios y confirmación del paciente ---------------------
    COLUMNAS_RECORDATORIO = {1: "recordatorio_1", 2: "recordatorio_2"}

    def reclamar_recordatorio(self, cita_id: int, numero: int) -> bool:
        """Reserva el envío de un recordatorio (atómico: aunque haya dos procesos, solo uno lo envía)."""
        col = self.COLUMNAS_RECORDATORIO[numero]
        return self._escribir(f"UPDATE citas SET {col}=? WHERE id=? AND {col}='' AND estado='confirmada'",
                              (self._ahora(), cita_id)).rowcount == 1

    def liberar_recordatorio(self, cita_id: int, numero: int) -> None:
        """El envío falló: se podrá reintentar en el siguiente ciclo."""
        self._escribir(f"UPDATE citas SET {self.COLUMNAS_RECORDATORIO[numero]}='' WHERE id=?", (cita_id,))

    def marcar_confirmacion(self, negocio_id: str, cita_id: int, cliente: str, valor: str) -> bool:
        """valor: 'confirmo' o 'cambiar' (lo que respondió el paciente). Solo para citas confirmadas del propio paciente."""
        return self._escribir("UPDATE citas SET confirmacion=? WHERE id=? AND negocio_id=? AND cliente=? AND estado='confirmada'",
                              (valor, cita_id, negocio_id, cliente)).rowcount == 1

    def citas_entre(self, negocio_id: str, desde: str, hasta: str) -> list[sqlite3.Row]:
        return self.con.execute(
            "SELECT * FROM citas WHERE negocio_id=? AND inicio >= ? AND inicio < ? ORDER BY inicio",
            (negocio_id, desde, hasta),
        ).fetchall()

    def citas_de_cliente(self, negocio_id: str, cliente: str, desde: str | None = None) -> list[sqlite3.Row]:
        return self.con.execute(
            f"SELECT * FROM citas WHERE negocio_id=? AND cliente=? AND {_ACTIVOS_SQL} "
            "AND inicio >= ? ORDER BY inicio",
            (negocio_id, cliente, desde or self._ahora()),
        ).fetchall()

    def cancelar_cita(self, negocio_id: str, cliente: str, cita_id: int) -> bool:
        cur = self._escribir(
            f"UPDATE citas SET estado='cancelada' WHERE id=? AND negocio_id=? AND cliente=? AND {_ACTIVOS_SQL}",
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

    # --- Usuarios, sesiones y bitácora ---------------------------------
    def crear_usuario(self, negocio_id: str, usuario: str, nombre: str, rol: str, profesional: str, clave_hash: str) -> int:
        try:
            return self._escribir(
                "INSERT INTO usuarios (negocio_id, usuario, nombre, rol, profesional, clave_hash, creado) VALUES (?,?,?,?,?,?,?)",
                (negocio_id, usuario.strip().lower(), nombre.strip(), rol, profesional, clave_hash, self._ahora())).lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"Ya existe el usuario '{usuario}'.")

    def usuario_por_login(self, negocio_id: str, usuario: str) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM usuarios WHERE negocio_id=? AND usuario=?",
                                (negocio_id, usuario.strip().lower())).fetchone()

    def usuario(self, negocio_id: str, usuario_id: int) -> sqlite3.Row | None:
        return self.con.execute("SELECT * FROM usuarios WHERE negocio_id=? AND id=?", (negocio_id, usuario_id)).fetchone()

    def usuarios(self, negocio_id: str) -> list[sqlite3.Row]:
        return self.con.execute("SELECT id, usuario, nombre, rol, profesional, activo, creado FROM usuarios "
                                "WHERE negocio_id=? ORDER BY activo DESC, nombre", (negocio_id,)).fetchall()

    def cambiar_clave_usuario(self, negocio_id: str, usuario_id: int, clave_hash: str) -> bool:
        ok = self._escribir("UPDATE usuarios SET clave_hash=? WHERE id=? AND negocio_id=?",
                            (clave_hash, usuario_id, negocio_id)).rowcount == 1
        if ok:
            self.cerrar_sesiones_de(usuario_id)  # con la clave nueva hay que volver a entrar
        return ok

    def activar_usuario(self, negocio_id: str, usuario_id: int, activo: bool) -> bool:
        ok = self._escribir("UPDATE usuarios SET activo=? WHERE id=? AND negocio_id=?",
                            (1 if activo else 0, usuario_id, negocio_id)).rowcount == 1
        if ok and not activo:
            self.cerrar_sesiones_de(usuario_id)
        return ok

    def duenos_activos(self, negocio_id: str) -> int:
        return self.con.execute("SELECT COUNT(*) AS n FROM usuarios WHERE negocio_id=? AND rol='dueno' AND activo=1",
                                (negocio_id,)).fetchone()["n"]

    def crear_sesion(self, token_hash: str, usuario_id: int, horas: float = 12) -> None:
        expira = (datetime.fromisoformat(self._ahora()) + timedelta(hours=horas)).isoformat(timespec="seconds")
        self._escribir("INSERT INTO sesiones (token_hash, usuario_id, expira) VALUES (?,?,?)", (token_hash, usuario_id, expira))
        self._escribir("DELETE FROM sesiones WHERE expira < ?", (self._ahora(),))

    def sesion_vigente(self, token_hash: str) -> sqlite3.Row | None:
        return self.con.execute(
            "SELECT u.* FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id "
            "WHERE s.token_hash=? AND s.expira > ? AND u.activo=1", (token_hash, self._ahora())).fetchone()

    def cerrar_sesion(self, token_hash: str) -> None:
        self._escribir("DELETE FROM sesiones WHERE token_hash=?", (token_hash,))

    def cerrar_sesiones_de(self, usuario_id: int) -> None:
        self._escribir("DELETE FROM sesiones WHERE usuario_id=?", (usuario_id,))

    def registrar_bitacora(self, negocio_id: str, quien: str, rol: str, accion: str, detalle: str,
                           creado: str | None = None) -> None:
        """Quién hizo qué. Se escribe sin interrumpir la acción original si algo falla."""
        try:
            self._escribir("INSERT INTO bitacora (negocio_id, quien, rol, accion, detalle, creado) VALUES (?,?,?,?,?,?)",
                           (negocio_id, quien, rol, accion, detalle[:500], creado or self._ahora()))
        except sqlite3.Error:  # pragma: no cover - la bitácora nunca debe tumbar una cita
            pass

    def bitacora(self, negocio_id: str, desde: str, limite: int = 300) -> list[sqlite3.Row]:
        return self.con.execute("SELECT * FROM bitacora WHERE negocio_id=? AND creado >= ? ORDER BY id DESC LIMIT ?",
                                (negocio_id, desde, limite)).fetchall()

    # --- Salud del sistema (lo lee el monitoreo) -------------------------
    def poner_estado(self, clave: str, valor: str) -> None:
        self._escribir("INSERT OR REPLACE INTO estado (clave, valor, actualizado) VALUES (?,?,?)", (clave, valor, self._ahora()))

    def estado(self, clave: str) -> str | None:
        fila = self.con.execute("SELECT valor FROM estado WHERE clave=?", (clave,)).fetchone()
        return fila["valor"] if fila else None

    def registrar_fallo(self, negocio_id: str, tipo: str, detalle: str) -> None:
        """tipo: modelo | envio | atender | recordatorio | firma. Nunca debe tumbar quien lo llama."""
        try:
            self._escribir("INSERT INTO fallos (negocio_id, tipo, detalle, creado) VALUES (?,?,?,?)",
                           (negocio_id, tipo, detalle[:400], self._ahora()))
        except sqlite3.Error:  # pragma: no cover
            pass

    def fallos_desde(self, desde: str) -> dict[str, int]:
        filas = self.con.execute("SELECT tipo, COUNT(*) AS n FROM fallos WHERE creado >= ? GROUP BY tipo", (desde,)).fetchall()
        return {f["tipo"]: f["n"] for f in filas}

    # --- Autorización de tratamiento de datos (Ley 1581) ------------------
    def registrar_autorizacion(self, negocio_id: str, cliente: str, version: str) -> bool:
        """True si es la primera vez que se le muestra el aviso de privacidad a este paciente."""
        return self._escribir("INSERT OR IGNORE INTO autorizaciones (negocio_id, cliente, version, creado) VALUES (?,?,?,?)",
                              (negocio_id, cliente, version, self._ahora())).rowcount == 1

    # --- Derechos del titular de los datos (Ley 1581: acceso y supresión) -----
    def exportar_datos_paciente(self, negocio_id: str, cliente: str) -> dict:
        def filas(sql, *args):
            return [dict(f) for f in self.con.execute(sql, args).fetchall()]
        claves = (negocio_id, f"{negocio_id}@openai")
        return {
            "cliente": cliente,
            "autorizacion": filas("SELECT version, creado FROM autorizaciones WHERE negocio_id=? AND cliente=?", negocio_id, cliente),
            "citas": filas("SELECT id, nombre, servicio, inicio, fin, estado, profesional, origen, creado FROM citas "
                           "WHERE negocio_id=? AND cliente=? ORDER BY inicio", negocio_id, cliente),
            "interesados": filas("SELECT nombre, interes, notas, creado FROM prospectos WHERE negocio_id=? AND cliente=?", negocio_id, cliente),
            "casos": filas("SELECT motivo, estado, creado FROM escalaciones WHERE negocio_id=? AND cliente=?", negocio_id, cliente),
            "mensajes_equipo_y_pausas": filas("SELECT rol, texto, origen, creado FROM mensajes_chat WHERE negocio_id=? AND cliente=? ORDER BY id",
                                              negocio_id, cliente),
            "conversaciones": filas("SELECT negocio_id AS clave, mensajes, actualizado FROM conversaciones "
                                    "WHERE negocio_id IN (?,?) AND cliente=?", *claves, cliente),
        }

    def eliminar_datos_paciente(self, negocio_id: str, cliente: str) -> dict:
        """Derecho de supresión: borra conversaciones y datos de contacto, cancela citas futuras y deja las pasadas sin
        nombre ni teléfono (la agenda conserva el hueco, no la persona). Los nombres que ya estén escritos dentro de un texto
        libre del historial de cambios no se pueden localizar de forma automática."""
        with self.transaccion() as con:
            claves = (negocio_id, f"{negocio_id}@openai")
            n = {"conversaciones": con.execute("DELETE FROM conversaciones WHERE negocio_id IN (?,?) AND cliente=?", (*claves, cliente)).rowcount,
                 "mensajes": con.execute("DELETE FROM mensajes_chat WHERE negocio_id=? AND cliente=?", (negocio_id, cliente)).rowcount,
                 "interesados": con.execute("DELETE FROM prospectos WHERE negocio_id=? AND cliente=?", (negocio_id, cliente)).rowcount,
                 "casos": con.execute("DELETE FROM escalaciones WHERE negocio_id=? AND cliente=?", (negocio_id, cliente)).rowcount}
            con.execute("DELETE FROM pausas WHERE negocio_id=? AND cliente=?", (negocio_id, cliente))
            con.execute("DELETE FROM autorizaciones WHERE negocio_id=? AND cliente=?", (negocio_id, cliente))
            n["citas_futuras_canceladas"] = con.execute(
                f"UPDATE citas SET estado='cancelada' WHERE negocio_id=? AND cliente=? AND {_ACTIVOS_SQL} AND inicio >= ?",
                (negocio_id, cliente, self._ahora())).rowcount
            n["citas_anonimizadas"] = con.execute(
                "UPDATE citas SET nombre='Paciente eliminado', cliente='eliminado' WHERE negocio_id=? AND cliente=?",
                (negocio_id, cliente)).rowcount
            con.execute("UPDATE bitacora SET detalle=replace(detalle, ?, '[eliminado]') WHERE negocio_id=? AND detalle LIKE ?",
                        (cliente, negocio_id, f"%{cliente}%"))
        return n

    # --- Idempotencia del webhook (Meta reintenta entregas) -------------
    def marcar_procesado(self, mensaje_id: str) -> bool:
        """Devuelve False si el mensaje ya se había procesado."""
        cur = self._escribir("INSERT OR IGNORE INTO mensajes_procesados (id) VALUES (?)", (mensaje_id,))
        return cur.rowcount == 1
