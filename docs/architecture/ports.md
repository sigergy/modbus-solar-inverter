# Arquitectura: ports

Documento vivo. Un único puerto de salida, en `custom_components/modbus_solar/ports/device.py`. Solo importa `domain` (`device.py:6`).

## `DeviceGateway` (`device.py:9-12`)

`typing.Protocol` con un método:

```python
async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]
```

Contrato (`device.py:11`):

- **Entrada:** una secuencia de `RegisterSpec`.
- **Salida:** un mapa de cada `RegisterSpec` pedido a sus **palabras crudas** de 16 bits, `dtype.words` por registro. No decodifica: eso es de `domain.decode`.
- **Errores:** `DeviceUnavailable` si el equipo no responde, `DeviceProtocolError` si responde mal (`custom_components/modbus_solar/domain/errors.py:4-9`). El contrato no admite otras: quien implemente el puerto traduce las suyas.

## Implementaciones

| Implementación | Dónde | Uso |
|---|---|---|
| `ModbusGateway` | `custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:19` | producción: ver [outbound](adapters/outbound.md) |
| `FakeGateway` | `tests/fakes.py:11-23` | tests: devuelve `words[address]` o lanza `error` |

## Consumidores

- `read_tier` (`custom_components/modbus_solar/application/poller.py:21-26`).
- `probe_device` (`custom_components/modbus_solar/application/probe.py:8`).
- `TierCoordinator` y `DeviceRuntime` lo guardan sin conocer la implementación (`custom_components/modbus_solar/adapters/inbound/coordinator.py:30`, `custom_components/modbus_solar/adapters/inbound/runtime.py:23`).
- `DeviceSubentryFlow` lo recibe a través de `gateway_factory` (`custom_components/modbus_solar/adapters/inbound/flow.py:36-38`).
