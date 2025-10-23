"""
Entrypoint for running the weather MCP server through stdio.
"""

from __future__ import annotations

import argparse
import logging
import sys

from .weather_server import create_weather_server


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Servidor MCP que expone datos del clima usando Open-Meteo."
    )
    parser.add_argument(
        "transport",
        choices=["stdio"],
        help="Modo de transporte MCP. Actualmente sólo 'stdio' está disponible.",
    )
    args = parser.parse_args()

    _configure_logging()
    server = create_weather_server()
    logging.getLogger(__name__).info("Servidor iniciado con transporte %s", args.transport)
    server.run(args.transport, show_banner=False)


if __name__ == "__main__":
    main()
