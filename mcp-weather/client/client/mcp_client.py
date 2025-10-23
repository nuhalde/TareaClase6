"""
Asynchronous MCP client wrapper tailored for the Tkinter GUI.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Awaitable, Iterable, Sequence
from dataclasses import is_dataclass, asdict
import json
import ast
import logging

from fastmcp.client import Client
from fastmcp.client.client import CallToolResult
from fastmcp.exceptions import ToolError

from .subprocess_utils import create_stdio_transport

DEFAULT_TIMEOUT = 30
logger = logging.getLogger(__name__)


def _normalize_payload(value: Any) -> Any:
    """
    Convert Pydantic/BaseModel/iterables into plain Python structures.
    """
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if hasattr(value, "_asdict"):
        return value._asdict()
    if is_dataclass(value):
        return {key: _normalize_payload(val) for key, val in asdict(value).items()}
    if hasattr(value, "__dict__") and value.__dict__:
        return {
            key: _normalize_payload(val) for key, val in value.__dict__.items()
        }
    if isinstance(value, dict):
        return {key: _normalize_payload(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_normalize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_payload(item) for item in value]
    if isinstance(value, set):
        return [_normalize_payload(item) for item in value]
    return value

class WeatherMCPClient:
    """
    Wrapper that manages a FastMCP stdio client on a dedicated asyncio loop.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._loop_ready = threading.Event()
        self._thread = threading.Thread(target=self._loop_worker, daemon=True)
        self._lock: asyncio.Lock | None = None
        self._client: Client | None = None
        self._shutdown = False

        self._thread.start()
        self._loop_ready.wait()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _loop_worker(self) -> None:
        asyncio.set_event_loop(self._loop)
        transport = create_stdio_transport(keep_alive=True)
        self._client = Client(transport=transport, name="mcp-weather-gui")
        self._lock = asyncio.Lock()
        self._loop_ready.set()

        try:
            self._loop.run_forever()
        finally:
            pending = asyncio.all_tasks()
            for task in pending:
                task.cancel()
            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()

    def _ensure_client(self) -> Client:
        if self._client is None:
            raise RuntimeError("El cliente MCP aún no está inicializado.")
        return self._client

    def _ensure_lock(self) -> asyncio.Lock:
        if self._lock is None:
            raise RuntimeError("El cliente MCP aún no está inicializado.")
        return self._lock

    @staticmethod
    def _unwrap_result(result: CallToolResult) -> Any:
        if result.data is not None:
            return _normalize_payload(result.data)
        if result.structured_content is not None:
            return _normalize_payload(result.structured_content)
        contents: list[str] = []
        for block in result.content:
            text = getattr(block, "text", None)
            if text is not None:
                contents.append(text)
        if len(contents) == 1:
            text = contents[0]
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                try:
                    return ast.literal_eval(text)
                except (ValueError, SyntaxError):
                    pass
        return contents

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, coro: Awaitable[Any]) -> Future:
        """
        Schedule a coroutine on the internal event loop.
        """
        if self._shutdown:
            raise RuntimeError("El cliente MCP ya fue cerrado.")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def warmup(self) -> Future:
        """
        Ensure the server is reachable by listing its tools once.
        """
        return self.submit(self._warmup_async())

    def search_cities(self, query: str) -> Future:
        return self.submit(self._search_cities_async(query))

    def fetch_weather_bundle(
        self,
        lat: float,
        lon: float,
        *,
        hours: int,
        unit: str,
    ) -> Future:
        return self.submit(
            self._fetch_weather_bundle_async(lat, lon, hours=hours, unit=unit)
        )

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._shutdown_async(), self._loop
            )
            future.result(timeout=DEFAULT_TIMEOUT)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=DEFAULT_TIMEOUT)

    # ------------------------------------------------------------------
    # Coroutine implementations
    # ------------------------------------------------------------------

    async def _warmup_async(self) -> Sequence[Any]:
        client = self._ensure_client()
        lock = self._ensure_lock()
        async with lock:
            async with client:
                tools = await client.list_tools()
                return tuple(tool.name for tool in tools)

    async def _search_cities_async(self, query: str) -> list[dict[str, Any]]:
        client = self._ensure_client()
        lock = self._ensure_lock()
        async with lock:
            async with client:
                result = await client.call_tool(
                    "search_city",
                    {"query": query},
                    timeout=DEFAULT_TIMEOUT,
                )
        data = self._unwrap_result(result)
        if isinstance(data, list):
            return data
        if isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
            return list(data)
        raise ToolError("Respuesta inesperada del servidor al buscar ciudades.")

    async def _fetch_weather_bundle_async(
        self,
        lat: float,
        lon: float,
        *,
        hours: int,
        unit: str,
    ) -> dict[str, Any]:
        client = self._ensure_client()
        lock = self._ensure_lock()
        async with lock:
            async with client:
                current_result = await client.call_tool(
                    "current_weather",
                    {"lat": lat, "lon": lon, "unit": unit},
                    timeout=DEFAULT_TIMEOUT,
                )
                forecast_result = await client.call_tool(
                    "forecast",
                    {"lat": lat, "lon": lon, "hours": hours, "unit": unit},
                    timeout=DEFAULT_TIMEOUT,
                )

        current_payload = self._unwrap_result(current_result)
        forecast_payload = self._unwrap_result(forecast_result)
        logger.debug("Clima actual bruto recibido: %r", current_payload)
        logger.debug("Pronóstico bruto recibido: %r", forecast_payload)

        current_payload = _normalize_payload(current_payload)
        forecast_payload = _normalize_payload(forecast_payload)

        if not isinstance(current_payload, dict):
            if isinstance(current_payload, Iterable) and not isinstance(
                current_payload, (str, bytes)
            ):
                current_payload = dict(current_payload)
            else:
                raise ToolError("Respuesta inesperada para el clima actual.")

        if isinstance(forecast_payload, dict):
            if "result" in forecast_payload:
                forecast_payload = forecast_payload["result"]
            else:
                raise ToolError("Respuesta inesperada para el pronóstico.")

        if not isinstance(forecast_payload, Iterable) or isinstance(
            forecast_payload, (str, bytes)
        ):
            raise ToolError("Respuesta inesperada para el pronóstico.")

        return {
            "current": current_payload,
            "forecast": list(forecast_payload),
        }

    async def _shutdown_async(self) -> None:
        lock = self._ensure_lock()
        client = self._ensure_client()
        async with lock:
            await client.close()


__all__ = ["WeatherMCPClient"]
