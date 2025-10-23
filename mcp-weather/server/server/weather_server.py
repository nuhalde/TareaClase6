"""
FastMCP server exposing weather-related tools backed by Open-Meteo.
"""

from __future__ import annotations

import logging
from typing import Literal, TypedDict, cast

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from .open_meteo import (
    OpenMeteoError,
    geocode,
    get_current,
    get_forecast,
)

logger = logging.getLogger(__name__)

UnitSystem = Literal["metric", "imperial"]


class CityResult(TypedDict):
    name: str
    country: str
    lat: float
    lon: float


class CurrentWeatherResult(TypedDict, total=False):
    temperature: float
    wind_speed: float
    humidity: float | None
    time: str
    unit: UnitSystem


class ForecastEntry(TypedDict):
    time: str
    temperature: float
    wind_speed: float
    precipitation: float
    unit: UnitSystem


def _normalize_unit(unit: str | None) -> UnitSystem:
    if not unit:
        return "metric"
    normalized = unit.strip().lower()
    if normalized in {"metric", "m", "si"}:
        return "metric"
    if normalized in {"imperial", "i", "us"}:
        return "imperial"
    raise ToolError("Unidad no soportada. Usa 'metric' o 'imperial'.")


def _validate_coordinates(lat: float, lon: float) -> tuple[float, float]:
    try:
        lat_value = float(lat)
        lon_value = float(lon)
    except (TypeError, ValueError) as exc:
        raise ToolError("Las coordenadas deben ser numéricas.") from exc
    if not -90.0 <= lat_value <= 90.0:
        raise ToolError("Latitud fuera de rango (-90 a 90).")
    if not -180.0 <= lon_value <= 180.0:
        raise ToolError("Longitud fuera de rango (-180 a 180).")
    return lat_value, lon_value


def _validate_hours(hours: int) -> int:
    if hours is None:
        return 24
    try:
        value = int(hours)
    except (TypeError, ValueError) as exc:
        raise ToolError("El parámetro 'hours' debe ser un entero.") from exc
    if value <= 0:
        raise ToolError("El número de horas debe ser mayor a 0.")
    if value > 168:
        raise ToolError("El pronóstico máximo permitido es de 168 horas (7 días).")
    return value


def create_weather_server() -> FastMCP:
    """
    Create and configure the FastMCP server with weather tools.
    """

    server = FastMCP("mcp-weather-server")

    @server.tool(
        name="search_city",
        description=(
            "Busca ciudades por nombre y devuelve una lista corta de coincidencias "
            "con país y coordenadas."
        ),
        title="Buscar ciudad",
    )
    def search_city(context: Context, query: str) -> list[CityResult]:
        if query is None or not query.strip():
            raise ToolError("El parámetro 'query' es obligatorio.")

        cleaned_query = query.strip()
        logger.info("Buscando ciudad: %s", cleaned_query)

        try:
            results = geocode(cleaned_query)
        except OpenMeteoError as exc:
            logger.error("Error en geocodificación: %s", exc)
            raise ToolError(str(exc)) from exc

        logger.info("Resultados encontrados: %d", len(results))
        return cast(list[CityResult], results)

    @server.tool(
        name="current_weather",
        description=(
            "Obtiene el clima actual para una latitud/longitud dadas. "
            "Unidades soportadas: metric o imperial."
        ),
        title="Clima actual",
    )
    def current_weather(
        context: Context, lat: float, lon: float, unit: str = "metric"
    ) -> CurrentWeatherResult:
        normalized_unit = _normalize_unit(unit)
        latitude, longitude = _validate_coordinates(lat, lon)

        logger.info(
            "Consultando clima actual lat=%s lon=%s unit=%s",
            latitude,
            longitude,
            normalized_unit,
        )

        try:
            current = get_current(latitude, longitude, normalized_unit)
        except OpenMeteoError as exc:
            logger.error("Error obteniendo clima actual: %s", exc)
            raise ToolError(str(exc)) from exc

        return cast(CurrentWeatherResult, current)

    @server.tool(
        name="forecast",
        description=(
            "Obtiene un pronóstico horario limitado en horas para una latitud/longitud. "
            "El máximo permitido son 168 horas."
        ),
        title="Pronóstico horario",
    )
    def forecast(
        context: Context,
        lat: float,
        lon: float,
        hours: int = 24,
        unit: str = "metric",
    ) -> list[ForecastEntry]:
        normalized_unit = _normalize_unit(unit)
        latitude, longitude = _validate_coordinates(lat, lon)
        limit_hours = _validate_hours(hours)

        logger.info(
            "Consultando pronóstico lat=%s lon=%s unit=%s horas=%s",
            latitude,
            longitude,
            normalized_unit,
            limit_hours,
        )

        try:
            forecast_data = get_forecast(latitude, longitude, limit_hours, normalized_unit)
        except OpenMeteoError as exc:
            logger.error("Error obteniendo pronóstico: %s", exc)
            raise ToolError(str(exc)) from exc

        return cast(list[ForecastEntry], forecast_data)

    return server


__all__ = [
    "CityResult",
    "CurrentWeatherResult",
    "ForecastEntry",
    "UnitSystem",
    "create_weather_server",
]
