# Guía de Instalación y Uso

## 1) Prerrequisitos
- Descarga e instala **Python 3.11 o superior** desde [python.org](https://www.python.org/downloads/windows/).
- Durante la instalación marca la opción *Add Python to PATH*.
- Verifica la instalación abriendo **PowerShell** y ejecutando:

```powershell
python --version
```

Debe mostrar una versión `Python 3.11.x` (o superior).

## 2) Descargar o clonar el proyecto
- Descarga o clona el repositorio y coloca la carpeta `mcp-weather/` en el directorio que prefieras.

## 3) Crear entorno virtual e instalar dependencias
En PowerShell, ubícate dentro de la carpeta `mcp-weather/` y ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 4) Probar el servidor
- Desde la carpeta `mcp-weather/` ejecuta:

```powershell
run_server.bat
```

O directamente:

```powershell
python -m server stdio
```

**Salida esperada** (resumen):

```
YYYY-MM-DD HH:MM:SS [INFO] server.server.__main__: Servidor iniciado con transporte stdio
```

El proceso quedará a la espera de conexiones MCP. Presiona `Ctrl+C` para detenerlo si lo ejecutaste manualmente.

## 5) Probar el cliente
- En otra ventana de PowerShell (o tras detener el servidor) ejecuta:

```powershell
run_client.bat
```

O bien:

```powershell
python -m client
```

Se abrirá la interfaz Tkinter y el servidor se iniciará automáticamente como subproceso.

## 6) Uso típico
1. Escribe **“Montevideo”** en el campo de búsqueda y presiona **Buscar**.
2. Selecciona la coincidencia correcta en la lista.
3. Observa el panel de **Clima actual** y la tabla de **Pronóstico 24h**.
4. Cambia unidades a **imperial** para ver la conversión instantánea (°F, mph, in).
5. El auto-refresh actualiza automáticamente cada 5 minutos (valor configurable).

## 7) Solución de problemas (FAQ)
- **Firewall/antivirus bloquea el subproceso**  
  - Permite la ejecución de Python (`python.exe`) en tu firewall/antivirus o marca la carpeta como segura.
- **Sin conexión a Internet**  
  - Aparecerá un mensaje de error. Verifica tu red y vuelve a intentar; el cliente reintenta la consulta.
- **Ciudad no encontrada**  
  - Ajusta el término de búsqueda (incluye país o provincia si aplica).
- **“No tools found”**  
  - Cierra el cliente y vuelve a abrirlo; también puedes ejecutar primero `python -m server stdio` para comprobar que arranca sin errores.

## 8) Estructura del proyecto y cómo extender
- La estructura principal es:

```
mcp-weather/
├─ server/...
├─ client/...
└─ docs/...
```

- Para añadir una nueva tool, por ejemplo `alerts`, implementa la lógica en `server/server/open_meteo.py` y regístrala en `server/server/weather_server.py`.
- Para cambiar el intervalo de auto-refresh, modifica el valor por defecto en `client/client/gui.py` (`self.auto_refresh_var = tk.IntVar(value=5)`).
