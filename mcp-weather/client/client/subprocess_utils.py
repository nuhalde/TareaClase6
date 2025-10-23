"""
Utilities for launching and terminating the MCP weather server subprocess.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastmcp.client.transports import StdioTransport

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def detect_python_executable() -> str:
    """
    Return the Python executable to use for spawning the server.
    Prefers a local .venv if available, otherwise falls back to the current interpreter.
    """
    if os.name == "nt":
        candidate = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = PROJECT_ROOT / ".venv" / "bin" / "python"
    if candidate.exists():
        logger.debug("Usando intérprete de la venv: %s", candidate)
        return str(candidate)
    logger.debug("Usando intérprete actual: %s", sys.executable)
    return sys.executable


def build_stdio_command() -> Tuple[str, List[str], Dict[str, str], str]:
    """
    Build command, arguments, environment and working directory for the server process.
    """
    command = detect_python_executable()
    args = ["-m", "server", "stdio"]
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    cwd = str(PROJECT_ROOT)
    logger.debug("Comando del servidor: %s %s (cwd=%s)", command, " ".join(args), cwd)
    return command, args, env, cwd


def create_stdio_transport(*, keep_alive: bool = True) -> StdioTransport:
    """
    Create a FastMCP stdio transport configured for the weather server.
    """
    command, args, env, cwd = build_stdio_command()
    return StdioTransport(
        command=command,
        args=args,
        env=env,
        cwd=cwd,
        keep_alive=keep_alive,
    )


def terminate_process(
    process: subprocess.Popen[Any] | None,
    *,
    timeout: float = 5.0,
) -> None:
    """
    Terminate a subprocess gracefully and escalate to kill if required.
    """
    if process is None:
        return
    if process.poll() is not None:
        return

    logger.info("Solicitando cierre del servidor MCP (PID %s)", process.pid)
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.warning("Forzando cierre del servidor MCP (PID %s)", process.pid)
        process.kill()


__all__ = [
    "build_stdio_command",
    "create_stdio_transport",
    "detect_python_executable",
    "terminate_process",
]
