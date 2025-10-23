"""
Tkinter-based GUI that consumes the MCP weather server.
"""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional

from fastmcp.exceptions import ToolError

from .mcp_client import WeatherMCPClient

logger = logging.getLogger(__name__)


class WeatherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MCP Weather")
        self.root.geometry("900x640")

        self.client = WeatherMCPClient()

        self.query_var = tk.StringVar()
        self.unit_var = tk.StringVar(value="metric")
        self.auto_refresh_var = tk.IntVar(value=5)

        self.current_vars: Dict[str, tk.StringVar] = {
            "temperature": tk.StringVar(value="--"),
            "wind": tk.StringVar(value="--"),
            "humidity": tk.StringVar(value="--"),
            "time": tk.StringVar(value="--"),
        }
        self.status_var = tk.StringVar(value="Inicializando cliente MCP…")

        self.city_results: List[Dict[str, Any]] = []
        self.selected_city: Optional[Dict[str, Any]] = None
        self._refresh_job: Optional[str] = None

        self._build_ui()
        self._bind_events()
        self._warmup()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        search_frame = ttk.LabelFrame(self.root, text="Búsqueda de ciudad")
        search_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Ciudad:").grid(row=0, column=0, padx=6, pady=6)
        search_entry = ttk.Entry(search_frame, textvariable=self.query_var)
        search_entry.grid(row=0, column=1, padx=6, pady=6, sticky="ew")

        search_button = ttk.Button(search_frame, text="Buscar", command=self._on_search)
        search_button.grid(row=0, column=2, padx=6, pady=6)

        unit_label = ttk.Label(search_frame, text="Unidades:")
        unit_label.grid(row=0, column=3, padx=6, pady=6)
        unit_combo = ttk.Combobox(
            search_frame,
            textvariable=self.unit_var,
            values=("metric", "imperial"),
            state="readonly",
            width=10,
        )
        unit_combo.grid(row=0, column=4, padx=6, pady=6)

        results_frame = ttk.LabelFrame(self.root, text="Resultados")
        results_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        self.city_listbox = tk.Listbox(results_frame, height=6, exportselection=False)
        self.city_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=self.city_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.city_listbox.config(yscrollcommand=scrollbar.set)

        current_frame = ttk.LabelFrame(self.root, text="Clima actual")
        current_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        for idx in range(4):
            current_frame.columnconfigure(idx, weight=1)

        ttk.Label(current_frame, text="Temperatura").grid(
            row=0, column=0, padx=4, pady=4
        )
        ttk.Label(current_frame, textvariable=self.current_vars["temperature"]).grid(
            row=1, column=0, padx=4, pady=4
        )

        ttk.Label(current_frame, text="Viento").grid(row=0, column=1, padx=4, pady=4)
        ttk.Label(current_frame, textvariable=self.current_vars["wind"]).grid(
            row=1, column=1, padx=4, pady=4
        )

        ttk.Label(current_frame, text="Humedad").grid(row=0, column=2, padx=4, pady=4)
        ttk.Label(current_frame, textvariable=self.current_vars["humidity"]).grid(
            row=1, column=2, padx=4, pady=4
        )

        ttk.Label(current_frame, text="Hora de referencia").grid(
            row=0, column=3, padx=4, pady=4
        )
        ttk.Label(current_frame, textvariable=self.current_vars["time"]).grid(
            row=1, column=3, padx=4, pady=4
        )

        forecast_frame = ttk.LabelFrame(self.root, text="Pronóstico horario")
        forecast_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=8)
        forecast_frame.columnconfigure(0, weight=1)
        forecast_frame.rowconfigure(0, weight=1)

        columns = ("time", "temperature", "wind", "precip")
        self.forecast_tree = ttk.Treeview(
            forecast_frame,
            columns=columns,
            show="headings",
            height=12,
        )
        self.forecast_tree.heading("time", text="Hora")
        self.forecast_tree.heading("temperature", text="Temp.")
        self.forecast_tree.heading("wind", text="Viento")
        self.forecast_tree.heading("precip", text="Precip.")
        self.forecast_tree.column("time", width=140, anchor="center")
        self.forecast_tree.column("temperature", width=120, anchor="center")
        self.forecast_tree.column("wind", width=120, anchor="center")
        self.forecast_tree.column("precip", width=120, anchor="center")
        self.forecast_tree.grid(row=0, column=0, sticky="nsew")

        tree_scroll = ttk.Scrollbar(
            forecast_frame, orient="vertical", command=self.forecast_tree.yview
        )
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.forecast_tree.configure(yscrollcommand=tree_scroll.set)

        controls_frame = ttk.Frame(self.root)
        controls_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=8)
        controls_frame.columnconfigure(2, weight=1)

        refresh_button = ttk.Button(
            controls_frame, text="Actualizar", command=self._refresh_weather
        )
        refresh_button.grid(row=0, column=0, padx=6)

        ttk.Label(controls_frame, text="Auto-refresh (min):").grid(
            row=0, column=1, padx=6
        )
        spinbox = ttk.Spinbox(
            controls_frame,
            from_=1,
            to=60,
            textvariable=self.auto_refresh_var,
            width=5,
            command=self._on_refresh_interval_change,
        )
        spinbox.grid(row=0, column=2, padx=6, sticky="w")

        status_label = ttk.Label(
            controls_frame, textvariable=self.status_var, anchor="w"
        )
        status_label.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def _bind_events(self) -> None:
        self.city_listbox.bind("<<ListboxSelect>>", self._on_select_city)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # MCP interactions
    # ------------------------------------------------------------------

    def _warmup(self) -> None:
        future = self.client.warmup()
        self._attach_future(
            future,
            on_success=lambda _: self.status_var.set("Listo para consultas."),
            on_error=lambda exc: self.status_var.set(
                f"Error al iniciar el cliente MCP: {exc}"
            ),
        )

    def _on_search(self) -> None:
        query = self.query_var.get().strip()
        if not query:
            messagebox.showinfo("Búsqueda", "Ingresa una ciudad para buscar.")
            return
        self.status_var.set(f"Buscando “{query}”…")
        future = self.client.search_cities(query)
        self._attach_future(future, on_success=self._handle_search_results)

    def _handle_search_results(self, results: List[Dict[str, Any]]) -> None:
        self.city_results = results
        self.city_listbox.delete(0, tk.END)
        for item in results:
            display = f"{item.get('name', 'N/A')} - {item.get('country', '--')}"
            self.city_listbox.insert(tk.END, display)
        if results:
            self.status_var.set(f"{len(results)} resultados encontrados.")
            self.city_listbox.selection_clear(0, tk.END)
            self.city_listbox.selection_set(0)
            self.city_listbox.event_generate("<<ListboxSelect>>")
        else:
            self.status_var.set("Sin coincidencias. Ajusta la búsqueda.")
            self.selected_city = None
            self._clear_current_weather()
            self._clear_forecast()

    def _on_select_city(self, _event: Any) -> None:
        selection = self.city_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= len(self.city_results):
            return
        self.selected_city = self.city_results[index]
        self.status_var.set(
            f"Seleccionado: {self.selected_city.get('name', 'N/A')} - "
            f"{self.selected_city.get('country', '--')}"
        )
        self._refresh_weather()

    def _refresh_weather(self) -> None:
        if not self.selected_city:
            messagebox.showinfo(
                "Pronóstico", "Selecciona primero una ciudad de la lista."
            )
            return
        lat = self.selected_city["lat"]
        lon = self.selected_city["lon"]
        unit = self.unit_var.get()
        hours = 24
        self.status_var.set("Consultando clima…")
        future = self.client.fetch_weather_bundle(lat, lon, hours=hours, unit=unit)
        self._attach_future(future, on_success=self._update_weather_display)

    def _update_weather_display(self, bundle: Dict[str, Any]) -> None:
        current = bundle.get("current") or {}
        forecast = bundle.get("forecast") or []
        unit = current.get("unit", self.unit_var.get())
        self.current_vars["temperature"].set(self._format_temperature(current, unit))
        self.current_vars["wind"].set(self._format_wind(current, unit))
        self.current_vars["humidity"].set(self._format_humidity(current))
        self.current_vars["time"].set(self._format_time(current.get("time")))
        self._populate_forecast(forecast, unit)
        self.status_var.set("Clima actualizado correctamente.")
        self._schedule_refresh()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _attach_future(self, future, *, on_success=None, on_error=None):
        def _callback(fut):
            try:
                result = fut.result()
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Error en operación MCP", exc_info=exc)
                self.root.after(
                    0,
                    lambda err=exc: self._handle_error(err, on_error),
                )
            else:
                if on_success:
                    self.root.after(0, lambda: on_success(result))

        future.add_done_callback(_callback)

    def _handle_error(self, exc: Exception, extra_handler=None) -> None:
        if extra_handler:
            extra_handler(exc)
        message = str(exc)
        if isinstance(exc, ToolError):
            messagebox.showerror("MCP Server", message)
        else:
            messagebox.showerror("Error", message)
        self.status_var.set(f"Error: {message}")

    def _schedule_refresh(self) -> None:
        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        minutes = max(1, self.auto_refresh_var.get())
        interval_ms = minutes * 60 * 1000
        self._refresh_job = self.root.after(interval_ms, self._refresh_weather)

    def _on_refresh_interval_change(self) -> None:
        if self.selected_city:
            self._schedule_refresh()

    def _clear_current_weather(self) -> None:
        for var in self.current_vars.values():
            var.set("--")

    def _clear_forecast(self) -> None:
        for row in self.forecast_tree.get_children():
            self.forecast_tree.delete(row)

    def _populate_forecast(self, entries: List[Dict[str, Any]], unit: str) -> None:
        self._clear_forecast()
        for entry in entries:
            values = (
                self._format_time(entry.get("time")),
                self._format_temperature(entry, unit),
                self._format_wind(entry, unit),
                self._format_precip(entry, unit),
            )
            self.forecast_tree.insert("", tk.END, values=values)

    @staticmethod
    def _format_time(value: Any) -> str:
        if not value:
            return "--"
        if isinstance(value, (int, float)):
            return str(value)
        text = str(value)
        text = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return text
        return dt.strftime("%d/%m %H:%M")

    @staticmethod
    def _format_temperature(data: Dict[str, Any], unit: str) -> str:
        value = data.get("temperature")
        if value is None:
            return "--"
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "--"
        suffix = "°C" if unit == "metric" else "°F"
        return f"{value:.1f} {suffix}"

    @staticmethod
    def _format_wind(data: Dict[str, Any], unit: str) -> str:
        value = data.get("wind_speed")
        if value is None:
            return "--"
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "--"
        suffix = "km/h" if unit == "metric" else "mph"
        return f"{value:.1f} {suffix}"

    @staticmethod
    def _format_precip(data: Dict[str, Any], unit: str) -> str:
        value = data.get("precipitation")
        if value is None:
            return "--"
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "--"
        suffix = "mm" if unit == "metric" else "in"
        return f"{value:.1f} {suffix}"

    @staticmethod
    def _format_humidity(data: Dict[str, Any]) -> str:
        value = data.get("humidity")
        if value is None:
            return "--"
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "--"
        return f"{value:.0f}%"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
            self._refresh_job = None
        try:
            self.client.shutdown()
        finally:
            self.root.destroy()


def run_app() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("client.client.mcp_client").setLevel(logging.DEBUG)
    root = tk.Tk()
    WeatherApp(root)
    root.mainloop()


__all__ = ["run_app", "WeatherApp"]
