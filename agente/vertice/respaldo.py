"""Respaldos de la base de datos (citas, conversaciones, usuarios…): crear, verificar y restaurar.

    python -m vertice.respaldo crear                 copia consistente + verificación + compresión (+ cifrado + subida)
    python -m vertice.respaldo verificar             restaura el último respaldo en una carpeta temporal y comprueba que sirve
    python -m vertice.respaldo restaurar <archivo> <destino.db>

Variables:  VERTICE_DB, VERTICE_RESPALDOS (carpeta, ej. /var/lib/vertice/respaldos)
            VERTICE_RESPALDO_CLAVE   si existe, cada respaldo se cifra con AES-256 (openssl). GUÁRDALA en otro lugar: sin ella no se restaura.
            VERTICE_RESPALDO_SUBIR   comando para copiar el archivo a OTRO lugar (la copia que solo vive en el servidor no es un respaldo).
                                     Ej.: "rclone copy {archivo} remoto:vertice"  o  "scp {archivo} usuario@otro-servidor:respaldos/"

Los respaldos contienen datos de salud de pacientes: cifrarlos y subirlos a un lugar privado.
"""

from __future__ import annotations

import gzip
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

PREFIJO = "vertice-"
TABLAS_CLAVE = ("citas", "conversaciones", "usuarios", "prospectos")


class ErrorRespaldo(Exception):
    pass


def _openssl(modo: str, origen: Path, destino: Path, clave: str) -> None:
    orden = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-salt", "-in", str(origen), "-out", str(destino),
             "-pass", "env:VERTICE_RESPALDO_CLAVE"]
    if modo == "descifrar":
        orden.insert(2, "-d")
    r = subprocess.run(orden, env={**os.environ, "VERTICE_RESPALDO_CLAVE": clave}, capture_output=True, text=True)
    if r.returncode != 0:
        raise ErrorRespaldo(f"openssl falló ({modo}): {r.stderr.strip()[:200]}")


def _integridad(ruta: Path) -> dict:
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    try:
        resultado = con.execute("PRAGMA integrity_check").fetchone()[0]
        if resultado != "ok":
            raise ErrorRespaldo(f"La copia está dañada: {resultado}")
        existentes = {f[0] for f in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLAS_CLAVE if t in existentes}
    except sqlite3.DatabaseError as e:  # archivo que no es una base de datos, truncado, etc.
        raise ErrorRespaldo(f"La copia está dañada o no es una base de datos: {e}") from e
    finally:
        con.close()


def _aplicar_retencion(carpeta: Path, ahora: datetime, diarios: int, semanales: int) -> list[Path]:
    """Se conservan los últimos `diarios` días y, además, el respaldo de cada domingo durante `semanales` semanas."""
    archivos = sorted((f for f in carpeta.glob(PREFIJO + "*") if f.is_file() and f.name != "subida_ok.txt"), reverse=True)
    borrados = []
    for i, f in enumerate(archivos):
        try:
            fecha = datetime.strptime(f.name[len(PREFIJO):len(PREFIJO) + 13], "%Y%m%d-%H%M")
        except ValueError:
            continue
        edad = ahora - fecha
        conservar = i == 0 or edad <= timedelta(days=diarios) or (fecha.weekday() == 6 and edad <= timedelta(weeks=semanales))
        if not conservar:
            f.unlink()
            borrados.append(f)
    return borrados


def crear(ruta_db: str | Path, carpeta: str | Path, ahora: datetime | None = None, diarios: int = 14, semanales: int = 8,
          clave: str = "", subir: str = "") -> Path:
    """Devuelve la ruta del respaldo final. Lanza ErrorRespaldo si la copia no pasa la verificación."""
    ahora = ahora or datetime.now()
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"{PREFIJO}{ahora:%Y%m%d-%H%M}.db"
    with tempfile.TemporaryDirectory(dir=carpeta) as tmp:
        copia = Path(tmp) / nombre
        origen = sqlite3.connect(str(ruta_db))
        destino = sqlite3.connect(str(copia))
        try:
            origen.backup(destino)  # copia consistente aunque el servidor esté escribiendo
        finally:
            destino.close()
            origen.close()
        _integridad(copia)
        comprimido = Path(tmp) / (nombre + ".gz")
        with open(copia, "rb") as e, gzip.open(comprimido, "wb", compresslevel=6) as s:
            shutil.copyfileobj(e, s)
        final = carpeta / comprimido.name
        if clave:
            final = carpeta / (comprimido.name + ".enc")
            _openssl("cifrar", comprimido, final, clave)
        else:
            shutil.move(str(comprimido), final)
    final.chmod(0o600)  # solo el usuario del servicio puede leerlo
    _aplicar_retencion(carpeta, ahora, diarios, semanales)
    if subir:
        r = subprocess.run(shlex.split(subir.format(archivo=str(final))), capture_output=True, text=True)
        if r.returncode != 0:
            raise ErrorRespaldo(f"El respaldo quedó en el servidor pero NO se pudo subir: {r.stderr.strip()[:200]}")
        (carpeta / "subida_ok.txt").write_text(ahora.isoformat(timespec="seconds"))
    return final


def restaurar(archivo: str | Path, destino: str | Path, clave: str = "", sobrescribir: bool = False) -> dict:
    """Deja una base de datos usable en `destino` y devuelve cuántos registros tiene. No pisa una base existente sin permiso."""
    archivo, destino = Path(archivo), Path(destino)
    if destino.exists() and not sobrescribir:
        raise ErrorRespaldo(f"{destino} ya existe; usa otro destino o confirma que quieres reemplazarla.")
    with tempfile.TemporaryDirectory() as tmp:
        fuente = archivo
        if archivo.suffix == ".enc":
            if not clave:
                raise ErrorRespaldo("El respaldo está cifrado: falta VERTICE_RESPALDO_CLAVE.")
            fuente = Path(tmp) / "descifrado.gz"
            _openssl("descifrar", archivo, fuente, clave)
        plano = Path(tmp) / "base.db"
        try:
            with gzip.open(fuente, "rb") as e, open(plano, "wb") as s:
                shutil.copyfileobj(e, s)
        except (OSError, EOFError) as ex:
            raise ErrorRespaldo(f"No se pudo descomprimir el respaldo (¿clave equivocada o archivo dañado?): {ex}") from ex
        conteo = _integridad(plano)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(plano), destino)
    return conteo


def ultimo(carpeta: str | Path) -> Path | None:
    archivos = [f for f in Path(carpeta).glob(PREFIJO + "*") if f.is_file() and f.name != "subida_ok.txt"]
    return max(archivos, key=lambda f: f.name, default=None)


def verificar(carpeta: str | Path, clave: str = "") -> dict:
    """Prueba de restauración: abre el último respaldo en una carpeta temporal. Hacerla cada mes."""
    arch = ultimo(carpeta)
    if arch is None:
        raise ErrorRespaldo("No hay respaldos para verificar.")
    with tempfile.TemporaryDirectory() as tmp:
        conteo = restaurar(arch, Path(tmp) / "prueba.db", clave)
    return {"archivo": arch.name, "registros": conteo}


def main(argv: list[str]) -> int:
    ruta_db = os.environ.get("VERTICE_DB", "vertice.db")
    carpeta = os.environ.get("VERTICE_RESPALDOS", "respaldos")
    clave = os.environ.get("VERTICE_RESPALDO_CLAVE", "")
    try:
        if argv[:1] == ["crear"]:
            f = crear(ruta_db, carpeta, clave=clave, subir=os.environ.get("VERTICE_RESPALDO_SUBIR", ""))
            print(f"Respaldo creado: {f} ({f.stat().st_size / 1e6:.2f} MB)")
        elif argv[:1] == ["verificar"]:
            print(verificar(carpeta, clave))
        elif argv[:1] == ["restaurar"] and len(argv) == 3:
            print(restaurar(argv[1], argv[2], clave))
        else:
            print(__doc__)
            return 2
    except ErrorRespaldo as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
