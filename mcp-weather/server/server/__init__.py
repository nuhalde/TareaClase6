"""
Weather MCP server package exposing Open-Meteo backed tools.
"""

from .weather_server import create_weather_server

__all__ = ["create_weather_server"]
