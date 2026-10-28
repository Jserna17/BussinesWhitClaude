"""Usuarios del panel: roles, permisos y claves.

Roles:
- dueno:       todo (indicadores, agenda, conversaciones, casos, equipo e historial de cambios).
- recepcion:   resumen, agenda completa, conversaciones y casos. No administra usuarios ni ve el historial.
- odontologo:  solo su propia agenda; puede marcar asistió / no asistió. No ve conversaciones ni indicadores.

Las claves se guardan con PBKDF2-SHA256 (sal aleatoria por usuario); nunca en texto plano.
Crear el primer usuario de una clínica:  python -m vertice.usuarios crear <clinica> <usuario> "<Nombre>" <rol> [profesional]
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import secrets
import sys
from dataclasses import dataclass

from .negocio import Negocio

ROLES = ("dueno", "recepcion", "odontologo")
ROL_TEXTO = {"dueno": "Dueño", "recepcion": "Recepción", "odontologo": "Odontólogo"}
ITERACIONES = 200_000
MIN_CLAVE = 8

PERMISOS = {
    "dueno": {"autenticado", "resumen", "agenda_ver", "agenda_editar", "estado_cita", "chats", "casos", "equipo", "historial"},
    "recepcion": {"autenticado", "resumen", "agenda_ver", "agenda_editar", "estado_cita", "chats", "casos"},
    "odontologo": {"autenticado", "agenda_ver", "estado_cita"},
}


@dataclass(frozen=True)
class Sesion:
    """Quién está haciendo la petición."""
    negocio: Negocio
    usuario_id: int       # 0 = acceso de soporte con la clave de la clínica
    usuario: str
    nombre: str
    rol: str
    profesional: str = ""

    @property
    def permisos(self) -> set[str]:
        return PERMISOS[self.rol]

    @property
    def es_soporte(self) -> bool:
        return self.usuario_id == 0


def hashear(clave: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${base64.b64encode(sal).decode()}${base64.b64encode(h).decode()}"


def verificar(clave: str, almacenado: str) -> bool:
    try:
        _, iteraciones, sal, esperado = almacenado.split("$")
        h = hashlib.pbkdf2_hmac("sha256", clave.encode(), base64.b64decode(sal), int(iteraciones))
        return hmac.compare_digest(h, base64.b64decode(esperado))
    except (ValueError, TypeError):
        return False


def validar_clave(clave: str) -> str | None:
    """Devuelve el motivo si la clave no sirve, o None."""
    if len(clave) < MIN_CLAVE:
        return f"La clave debe tener al menos {MIN_CLAVE} caracteres."
    if not (any(c.isalpha() for c in clave) and any(c.isdigit() for c in clave)):
        return "La clave debe mezclar letras y números."
    return None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def nuevo_token() -> str:
    return secrets.token_urlsafe(32)


def _cli(argv: list[str]) -> int:
    from .app import RUTA_DB, CARPETA_NEGOCIOS
    from .db import BaseDatos
    from .negocio import cargar_negocios
    if len(argv) < 5 or argv[0] != "crear" or argv[4] not in ROLES:
        print(__doc__)
        return 2
    _, negocio_id, usuario, nombre, rol, *resto = argv
    negocios = cargar_negocios(CARPETA_NEGOCIOS)
    if negocio_id not in negocios:
        print(f"La clínica '{negocio_id}' no existe. Disponibles: {', '.join(negocios)}")
        return 1
    profesional = resto[0] if resto else ""
    if rol == "odontologo" and profesional not in negocios[negocio_id].nombres_profesionales():
        print(f"Un odontólogo necesita un profesional válido: {', '.join(negocios[negocio_id].nombres_profesionales())}")
        return 1
    clave = getpass.getpass("Clave (mínimo 8, con letras y números): ")
    motivo = validar_clave(clave)
    if motivo:
        print(motivo)
        return 1
    BaseDatos(RUTA_DB).crear_usuario(negocio_id, usuario, nombre, rol, profesional, hashear(clave))
    print(f"Usuario '{usuario}' creado en {negocio_id} como {ROL_TEXTO[rol]}.")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
