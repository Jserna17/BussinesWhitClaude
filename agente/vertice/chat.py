"""Simulador en la terminal: chatea con el asistente de un negocio sin WhatsApp.

Uso:  python -m vertice.chat clinica-demo
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .agente import Asistente
from .db import BaseDatos
from .negocio import cargar_negocios

RAIZ = Path(__file__).resolve().parent.parent


def main() -> None:
    negocios = cargar_negocios(RAIZ / "negocios")
    p = argparse.ArgumentParser(description="Chatea con el asistente de un negocio.")
    p.add_argument("negocio", choices=sorted(negocios))
    p.add_argument("--cliente", default="573000000000", help="Número simulado del cliente.")
    p.add_argument("--db", default=str(RAIZ / "simulador.db"))
    p.add_argument("--debug", action="store_true", help="Muestra herramientas y consumo de tokens.")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO if args.debug else logging.WARNING)

    negocio = negocios[args.negocio]
    asistente = Asistente(BaseDatos(args.db))
    print(f"Chat con {negocio.nombre}. Escribe 'salir' para terminar.\n")
    while True:
        try:
            texto = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if texto.lower() in {"salir", "exit"}:
            break
        if texto:
            print(f"\n{negocio.nombre}: {asistente.responder(negocio, args.cliente, texto)}\n")


if __name__ == "__main__":
    main()
