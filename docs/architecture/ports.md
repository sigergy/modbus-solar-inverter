# Arquitectura: ports

Documento vivo. Dos puertos de salida, en `custom_components/modbus_solar/ports/device.py`: uno lee y otro escribe. Solo importan `domain` (`device.py:6-7`).

## `DeviceGateway` (`device.py:10-13`)

`typing.Protocol` con un método:

```python
async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]
```

Contrato (`device.py:12`):

- **Entrada:** una secuencia de `RegisterSpec`.
- **Salida:** un mapa de cada `RegisterSpec` pedido a sus **palabras crudas** de 16 bits, `dtype.words` por registro. No decodifica: eso es de `domain.decode`.
- **Errores:** `DeviceUnavailable` si el equipo no responde, `DeviceProtocolError` si responde mal (`custom_components/modbus_solar/domain/errors.py:4-9`). El contrato no admite otras: quien implemente el puerto traduce las suyas.

## `DeviceWriter` (`device.py:16-21`)

`typing.Protocol` con un método. Va separado de `DeviceGateway` porque el poller y el config flow solo leen (`device.py:17`):

```python
async def write(self, spec: WriteSpec, value: float) -> None
```

Contrato (`device.py:20`):

- **Entrada:** un `WriteSpec` y el valor ya validado.
- **Salida:** nada. No relee: el equipo no expone el ajuste.
- **Errores:** `EncodeError` si el valor no cabe en el tipo, `DeviceUnavailable` si el equipo no responde, `DeviceProtocolError` si responde mal (`custom_components/modbus_solar/domain/errors.py:4-9`, `:16-17`).

## Implementaciones

| Implementación | Dónde | Uso |
|---|---|---|
| `ModbusGateway` | `custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:33` | producción, `read` (`:41-54`) y `write` (`:56-60`): un solo objeto implementa los dos puertos. Ver [outbound](adapters/outbound.md) |
| `FakeGateway` | `tests/fakes.py:12-24` | tests: devuelve `words[address]` o lanza `error` |
| `FakeWriter` | `tests/fakes.py:27-37` | tests: anota `(spec, valor)` en `writes` o lanza `error` |

## Consumidores

- `read_tier` (`custom_components/modbus_solar/application/poller.py:21-26`).
- `probe_device` (`custom_components/modbus_solar/application/probe.py:10`).
- `TierCoordinator` y `DeviceRuntime` lo guardan sin conocer la implementación (`custom_components/modbus_solar/adapters/inbound/coordinator.py:30`, `custom_components/modbus_solar/adapters/inbound/runtime.py:24`).
- `DeviceWriter`: `set_limit` y `set_enabled` (`custom_components/modbus_solar/application/control.py:9-20`). `DeviceRuntime` lo guarda (`custom_components/modbus_solar/adapters/inbound/runtime.py:25`) y `ModbusSolarControl` lo toma de ahí (`custom_components/modbus_solar/adapters/inbound/entities/control.py:31`).
- `DeviceConfigFlow` lo recibe a través de `gateway_factory` (`custom_components/modbus_solar/adapters/inbound/flow.py:37-40`, `:202-205`).
