# Arquitectura: adaptadores de salida

Documento vivo. Todo lo que habla con `modbus_connection`. Un único adaptador, en `custom_components/modbus_solar/adapters/outbound/modbus_gateway.py`. No importa `adapters.inbound` (`pyproject.toml:58-61`).

## `ModbusGateway` (`modbus_gateway.py:19-44`)

Implementa [`DeviceGateway`](../ports.md) sobre una `ModbusUnit` compartida de la integración `modbus` del core. La unit la obtiene la raíz (`custom_components/modbus_solar/__init__.py:37-40`, `custom_components/modbus_solar/config_flow.py:27-33`).

### Constructor (`modbus_gateway.py:20-25`)

`ModbusGateway(unit, profile)`.

- `max_gap = profile.max_gap` (`modbus_gateway.py:22`).
- `max_count = profile.max_block_registers` (`modbus_gateway.py:23`).
- Llama a `unit.set_message_spacing(profile.min_request_interval_s)`: la librería espacia las peticiones de esa unit dentro de la conexión compartida (`modbus_gateway.py:24-25`). Para los dos perfiles Ingeteam son 1,0 s (`custom_components/modbus_solar/profiles/ingeteam/oneplay.py:12`, `custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:96`).

### `read` (`modbus_gateway.py:27-44`)

1. **Bloques.** `plan_blocks(specs, max_gap, max_count)` agrupa los registros (`modbus_gateway.py:29`). Una petición por bloque. Con `max_gap=0` solo se fusionan registros contiguos o solapados. El STORAGE usa `max_gap=9` y `max_block_registers=10` (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:97-99`).
2. **Petición.** Un bloque `HOLDING` usa `read_holding_registers`; uno `INPUT`, `read_input_registers` (`modbus_gateway.py:30-35`).
3. **Longitud.** Si la respuesta no trae `block.count` registros, lanza `DeviceProtocolError` (`modbus_gateway.py:40-41`).
4. **Reparto.** Guarda cada palabra por `(kind, dirección)` (`modbus_gateway.py:42-43`) y devuelve, por cada `RegisterSpec`, sus `dtype.words` palabras (`modbus_gateway.py:44`).

Si falla un bloque, falla toda la lectura: un tier es todo o nada.

### Traducción de excepciones (`modbus_gateway.py:36-39`)

Es el único sitio que conoce las excepciones de `modbus_connection` (`modbus_gateway.py:5-11`).

| `modbus_connection` | Dominio |
|---|---|
| `ModbusConnectionError`, `ModbusTimeoutError` | `DeviceUnavailable` |
| `ModbusExceptionError`, `ModbusProtocolError` | `DeviceProtocolError` |

Se conserva la causa con `raise … from err`. El mensaje de la excepción de dominio es `str(err)`.

## Lo que no hace

- No decodifica: devuelve palabras crudas (`domain.decode` lo hace).
- No abre ni cierra la conexión. La abre y la libera HA a través de la entry (`custom_components/modbus_solar/__init__.py:36`); en el config flow, la unit temporal (`custom_components/modbus_solar/config_flow.py:24`).
- No traduce `HomeAssistantError` de la apertura: eso lo hace `open_gateway` (`custom_components/modbus_solar/config_flow.py:30-32`).
