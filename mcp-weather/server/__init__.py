"""
Convenience exports for the MCP weather server package.
"""

from .server.weather_server import create_weather_server

__all__ = ["create_weather_server"]
