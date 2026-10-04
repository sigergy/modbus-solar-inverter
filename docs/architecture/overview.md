# Arquitectura: visión general

Documento vivo. Describe el código de `custom_components/modbus_solar/`. Decisión de origen: [ADR 0001](../decisions/0001-hexagonal-import-linter.md).

## Capas

```
            ┌──────────────────────────────────────────────┐
 raíz       │ __init__.py · config_flow.py (composición)   │
            └───────────────┬──────────────────────────────┘
                            │ conoce todo, lo une
            ┌───────────────▼──────────────────────────────┐
 adapters   │ inbound (HA)          outbound (Modbus)      │  no se importan entre sí
            └───────────────┬──────────────────────────────┘
            ┌───────────────▼──────────────────────────────┐
 application│ Catalog · read_tier · probe_device           │
            │ set_limit · set_enabled                      │
            └───────────────┬──────────────────────────────┘
            ┌───────────────▼──────────────────────────────┐
 ports      │ DeviceGateway · DeviceWriter (Protocol)      │
            └───────────────┬──────────────────────────────┘
            ┌───────────────▼──────────────────────────────┐
 domain     │ tipos · perfil · energía · errores · decode  │
            │ blocks · validate · control · encode         │
            └──────────────────────────────────────────────┘

 profiles   datos de cada equipo; solo importan domain
```

Una capa solo importa las de debajo. `profiles` queda fuera de la pila: es dato, no lógica.

## Contratos de import-linter

Definidos en `pyproject.toml:21-61` y ejecutados por `scripts/lint.sh:12` y por el job `lint` (`.github/workflows/tests.yml:22-24`).

| Contrato | Qué prohíbe | Cita |
|---|---|---|
| `Hexagonal layers` | Una capa importa otra que está por encima en `adapters` > `application` > `ports` > `domain` | `pyproject.toml:25-33` |
| `Core does not import Home Assistant or Modbus` | `domain`, `ports`, `application` y `profiles` importan `homeassistant` o `modbus_connection` | `pyproject.toml:35-44` |
| `Profiles only import domain` | `profiles` importa `ports`, `application` o `adapters` | `pyproject.toml:46-50` |
| `Core does not know concrete profiles` | `domain`, `ports` y `application` importan `profiles` | `pyproject.toml:52-56` |
| `Inbound and outbound adapters are independent` | `adapters.inbound` y `adapters.outbound` se importan entre sí | `pyproject.toml:58-61` |

`include_external_packages = true` (`pyproject.toml:23`) hace que los contratos vean también `homeassistant` y `modbus_connection`.

Dos reglas más, sin contrato propio:

- Solo `ModbusGateway` conoce las excepciones de `modbus_connection` (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:6-12`, `:22-30`). Los adaptadores de entrada solo ven errores de dominio.
- Dentro del paquete solo se usan imports relativos.

## Flujo de datos

```
async_setup_entry
  └─ async_get_unit(hass, entry, ModbusTcpParams, unit_id)        __init__.py:28
       └─ ModbusGateway(unit, profile)                             __init__.py:29
            └─ build_runtime → un TierCoordinator por tier         __init__.py:32, runtime.py:71-85

TierCoordinator._async_update_data                                 coordinator.py:53
  └─ read_tier(tier, gateway, profile, keys)                       coordinator.py:55, poller.py:21
       ├─ ModbusGateway.read(specs)                                poller.py:31, modbus_gateway.py:41
       │    └─ ModbusUnit.read_holding_registers / read_input_registers (un bloque por petición)
       └─ decode(spec, words)                                      poller.py:38, decode.py:10
  ◄─ TierResult(values, raw, decode_errors)                        poller.py:14-18

ModbusSolarSensor.native_value = result.values[key]                factory.py:29-33
ModbusSolarEnergySensor._handle_coordinator_update                 entities/energy.py:35-41
  └─ EnergyAccumulator.add(t, suma de sources)                     domain/energy.py:38

ModbusSolarNumber.async_set_native_value                           entities/number.py:36-39
  └─ set_limit(writer, control, state, value)                      control.py:9-15
       └─ ModbusGateway.write(spec, value)                         modbus_gateway.py:56
            └─ encode(spec, value) → ModbusUnit.write_registers    encode.py:9, modbus_gateway.py:57-60

ModbusSolarSwitch._set(enabled)                                    entities/switch.py:40-43
  └─ set_enabled(writer, control, state, enabled)                  control.py:18-20
```

Rutas completas bajo `custom_components/modbus_solar/` (`adapters/inbound/` para `runtime.py`, `coordinator.py`, `entities/factory.py`, `entities/energy.py`, `entities/number.py` y `entities/switch.py`; `application/` para `poller.py` y `control.py`; `domain/` para `decode.py` y `encode.py`).

Las escrituras no pasan por el coordinator: el number y el switch llaman al caso de uso, que escribe primero y cambia el estado después. Si la escritura falla, el estado no cambia (`custom_components/modbus_solar/application/control.py:12-15`). Detalle: [features/control](../features/control.md).

- El primer refresh de cada coordinator se lanza en segundo plano: un equipo caído no retrasa el arranque de HA ni bloquea la entry (`custom_components/modbus_solar/__init__.py:35-37`).
- `always_update` va por tier. Por defecto es `False` y HA solo escribe estado si cambia el `TierResult` (`custom_components/modbus_solar/adapters/inbound/coordinator.py:33`, `:41-43`). Los tiers con fuentes de energía usan `True` para que la integral avance con potencia constante (`custom_components/modbus_solar/adapters/inbound/runtime.py:70`, `:81`).
- Las claves habilitadas se leen del entity registry en el setup (`custom_components/modbus_solar/__init__.py:30`, `custom_components/modbus_solar/adapters/inbound/runtime.py:47-57`). Una energía habilitada añade sus `sources` aunque su sensor de potencia esté deshabilitado (`custom_components/modbus_solar/adapters/inbound/runtime.py:53-56`). Habilitar o deshabilitar una entidad recarga la entry y con ella las claves (`docs/changes/2026-10-04-skeleton/spec.md:323-325`).

## Composición

Solo `__init__.py` y `config_flow.py` conocen a la vez adaptadores de entrada, de salida, catálogo y perfiles.

`custom_components/modbus_solar/__init__.py`:

- `CATALOG = Catalog(ALL_PROFILES)`: la raíz inyecta los perfiles al catálogo (`:20`).
- `async_setup_entry` crea el `DeviceRuntime` del equipo de la entry (`:25-32`), con el mismo `ModbusGateway` como lector y escritor (`:31-32`), lo guarda en `entry.runtime_data` (`:33`), lanza los primeros refresh (`:35-37`) y reenvía las plataformas (`:39`). Sin update listener: el reconfigure recarga la entry.
- `PLATFORMS = [SENSOR, NUMBER, SWITCH]` (`:21`).
- `async_migrate_entry` deja las entries v1 en `MIGRATION_ERROR` con un mensaje en el log (`:47-55`).
- `sensor.py:10-13`, `number.py:10-13`, `switch.py:10-13` y `diagnostics.py:12-19` son delegaciones finas a `adapters/inbound/`.

`custom_components/modbus_solar/config_flow.py`:

- `open_gateway` abre `async_get_temporary_unit`, traduce `HomeAssistantError` a `EndpointInUse` y entrega un `ModbusGateway` (`:20-33`).
- `ModbusSolarConfigFlow` inyecta `catalog` y `gateway_factory` en `DeviceConfigFlow` (`:36-38`).

Detalle por capa: [domain](domain.md), [application](application.md), [ports](ports.md), [inbound](adapters/inbound.md), [outbound](adapters/outbound.md).
