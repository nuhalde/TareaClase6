"""
Convenience wrappers for Open-Meteo's public APIs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

UnitSystem = Literal["metric", "imperial"]

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_TIMEOUT = 10
MAX_RESULTS = 8


class OpenMeteoError(RuntimeError):
    """Raised when Open-Meteo cannot satisfy a request."""


def _configure_session() -> Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


session = _configure_session()


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Perform a GET request and return the parsed JSON response.
    """
    try:
        response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
    except requests.Timeout as exc:
        raise OpenMeteoError("La consulta a Open-Meteo excedió el tiempo de espera.") from exc
    except requests.RequestException as exc:
        raise OpenMeteoError(f"No se pudo contactar Open-Meteo: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise OpenMeteoError("Open-Meteo devolvió una respuesta inválida.") from exc
    return data


def geocode(query: str, *, limit: int = MAX_RESULTS) -> list[dict[str, Any]]:
    """
    Resolve a free-text query into candidate cities with coordinates.
    """
    params = {
        "name": query,
        "count": limit,
        "language": "es",
        "format": "json",
    }
    payload = _request_json(GEOCODE_URL, params)
    candidates = payload.get("results") or []
    results: list[dict[str, Any]] = []

    for candidate in candidates:
        try:
            latitude = float(candidate["latitude"])
            longitude = float(candidate["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        results.append(
            {
                "name": candidate.get("name", "").strip() or "Sin nombre",
                "country": candidate.get("country", "N/A"),
                "lat": latitude,
                "lon": longitude,
            }
        )

    if not results:
        logger.info("Geocodificación sin resultados para %s", query)

    return results


def _unit_params(unit: UnitSystem) -> dict[str, str]:
    if unit == "imperial":
        return {
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
        }
    return {
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }


def get_current(lat: float, lon: float, unit: UnitSystem) -> dict[str, Any]:
    """
    Fetch current weather metrics for the provided coordinates.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "timezone": "auto",
        **_unit_params(unit),
    }
    payload = _request_json(FORECAST_URL, params)
    current = payload.get("current")
    if not current:
        raise OpenMeteoError("No hay datos de clima actual para estas coordenadas.")

    try:
        temperature = float(current["temperature_2m"])
        wind_speed = float(current["wind_speed_10m"])
    except (KeyError, TypeError, ValueError) as exc:
        raise OpenMeteoError("Datos incompletos de clima actual.") from exc

    humidity_raw = current.get("relative_humidity_2m")
    humidity: float | None
    try:
        humidity = float(humidity_raw) if humidity_raw is not None else None
    except (TypeError, ValueError):
        humidity = None

    return {
        "temperature": temperature,
        "wind_speed": wind_speed,
        "humidity": humidity,
        "time": str(current.get("time", "")),
        "unit": unit,
    }


def get_forecast(
    lat: float, lon: float, hours: int, unit: UnitSystem
) -> list[dict[str, Any]]:
    """
    Fetch hourly forecast entries limited to a number of hours.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,wind_speed_10m,precipitation",
        "timezone": "auto",
        **_unit_params(unit),
    }
    payload = _request_json(FORECAST_URL, params)
    hourly = payload.get("hourly")
    if not hourly:
        raise OpenMeteoError("No hay datos de pronóstico para estas coordenadas.")

    times = hourly.get("time") or []
    temperatures = hourly.get("temperature_2m") or []
    wind_speeds = hourly.get("wind_speed_10m") or []
    precipitation = hourly.get("precipitation") or []

    entries: list[dict[str, Any]] = []
    limit = min(hours, len(times))

    for index in range(limit):
        try:
            temperature = float(temperatures[index])
            wind_speed = float(wind_speeds[index])
            precip = float(precipitation[index])
        except (TypeError, ValueError, IndexError):
            continue
        entries.append(
            {
                "time": str(times[index]),
                "temperature": temperature,
                "wind_speed": wind_speed,
                "precipitation": precip,
                "unit": unit,
            }
        )

    if not entries:
        raise OpenMeteoError("No se pudieron construir datos de pronóstico utilizables.")

    return entries


__all__ = ["UnitSystem", "OpenMeteoError", "geocode", "get_current", "get_forecast"]
