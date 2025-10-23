# Pruebas Rápidas

## 1. Caso feliz: “Montevideo”
- Abre el cliente (`python -m client`).
- Busca “Montevideo”, selecciona la coincidencia de Uruguay.
- Verifica que el panel de clima actual muestre temperatura, viento y hora.
- La tabla de pronóstico debe listar 24 filas con hora, temperatura, viento y precipitación.

## 2. Ciudad ambigua: “San José”
- Ingresa “San José” y presiona **Buscar**.
- Observa múltiples coincidencias (Costa Rica, Estados Unidos, etc.).
- Selecciona cada opción y confirma que los resultados cambian según las coordenadas.

## 3. Sin conexión (simulado)
- Desconecta temporalmente la red o bloquea el acceso a internet.
- Ejecuta una búsqueda; debería aparecer un mensaje de error claro indicando problemas de conexión.
- Restablece la red y vuelve a buscar para confirmar la recuperación.

## 4. Cambio de unidades métrico/imperial
- Con una ciudad seleccionada, cambia el selector a **imperial**.
- Verifica que temperatura, viento y precipitación se conviertan (°F, mph, in).
- Regresa a **metric** y confirma la reconversión (°C, km/h, mm).

## 5. Cierre y reapertura del cliente
- Cierra la ventana principal; el servidor se detiene automáticamente.
- Vuelve a ejecutar `python -m client` y valida que la inicialización sea exitosa.
- Realiza una búsqueda rápida para confirmar el funcionamiento tras el reinicio.
