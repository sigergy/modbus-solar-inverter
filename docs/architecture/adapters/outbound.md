# Arquitectura: adaptadores de salida

Documento vivo. Todo lo que habla con `modbus_connection`. Un único adaptador, en `custom_components/modbus_solar/adapters/outbound/modbus_gateway.py`. No importa `adapters.inbound` (`pyproject.toml:58-61`).

## `ModbusGateway` (`modbus_gateway.py:33-60`)

Implementa [`DeviceGateway`](../ports.md) y [`DeviceWriter`](../ports.md) sobre una `ModbusUnit` compartida de la integración `modbus` del core. La unit la obtiene la raíz (`custom_components/modbus_solar/__init__.py:60`, `custom_components/modbus_solar/config_flow.py:27-33`). La raíz pasa el mismo objeto como lector y como escritor (`custom_components/modbus_solar/__init__.py:67-68`): dos puertos, una implementación.

### Constructor (`modbus_gateway.py:34-39`)

`ModbusGateway(unit, profile)`.

- `max_gap = profile.max_gap` (`modbus_gateway.py:36`).
- `max_count = profile.max_block_registers` (`modbus_gateway.py:37`).
- Llama a `unit.set_message_spacing(profile.min_request_interval_s)`: la librería espacia las peticiones de esa unit dentro de la conexión compartida (`modbus_gateway.py:38-39`). Para los dos perfiles Ingeteam son 1,0 s (`custom_components/modbus_solar/profiles/ingeteam/oneplay.py:12`, `custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:156`).

### `read` (`modbus_gateway.py:41-54`)

1. **Bloques.** `plan_blocks(specs, max_gap, max_count)` agrupa los registros (`modbus_gateway.py:43`). Una petición por bloque. Con `max_gap=0` solo se fusionan registros contiguos o solapados. El STORAGE usa `max_gap=9` y `max_block_registers=10` (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:157-159`).
2. **Petición.** Un bloque `HOLDING` usa `read_holding_registers`; uno `INPUT`, `read_input_registers` (`modbus_gateway.py:44-49`).
3. **Longitud.** Si la respuesta no trae `block.count` registros, lanza `DeviceProtocolError` (`modbus_gateway.py:50-51`).
4. **Reparto.** Guarda cada palabra por `(kind, dirección)` (`modbus_gateway.py:52-53`) y devuelve, por cada `RegisterSpec`, sus `spec.words` palabras (`modbus_gateway.py:54`).

Si falla un bloque, falla toda la lectura: un tier es todo o nada.

### `write` (`modbus_gateway.py:56-60`)

1. **Codificación.** `encode(spec, value)` devuelve las palabras de la trama (`modbus_gateway.py:57`). Es dominio puro y puede lanzar `EncodeError` (`custom_components/modbus_solar/domain/encode.py:9-19`).
2. **Escritura.** Una sola petición FC16 con `unit.write_registers(spec.address, words)` (`modbus_gateway.py:58-60`). El STORAGE exige que código, dato 1 y valor vayan juntos en una trama (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:77-80`).
3. **Errores.** Los de la librería pasan por la misma traducción que `read`.

No relee tras escribir: el equipo no expone el ajuste, así que no hay nada que contrastar (ADR [0012](../../decisions/0012-optimistic-restored-state.md)).

### Traducción de excepciones (`modbus_gateway.py:22-30`)

`_translated()` es un context manager que comparten `read` (`modbus_gateway.py:48`) y `write` (`modbus_gateway.py:59`). Es el único sitio que conoce las excepciones de `modbus_connection` (`modbus_gateway.py:6-12`).

| `modbus_connection` | Dominio |
|---|---|
| `ModbusConnectionError`, `ModbusTimeoutError` | `DeviceUnavailable` |
| `ModbusExceptionError`, `ModbusProtocolError` | `DeviceProtocolError` |

Se conserva la causa con `raise … from err`. El mensaje de la excepción de dominio es `str(err)`.

## Lo que no hace

- No decodifica: devuelve palabras crudas (`domain.decode` lo hace).
- No abre ni cierra la conexión. La abre y la libera HA a través de la entry (`custom_components/modbus_solar/__init__.py:59-60`); en el config flow, la unit temporal (`custom_components/modbus_solar/config_flow.py:24`).
- No traduce `HomeAssistantError` de la apertura: eso lo hace `open_gateway` (`custom_components/modbus_solar/config_flow.py:30-32`).
- No decide qué se escribe ni cuándo: recibe un `WriteSpec` y un valor ya validados por `application.control`.
