# Arquitectura: adaptadores de entrada

Documento vivo. Todo lo que habla con Home Assistant. Rutas bajo `custom_components/modbus_solar/adapters/inbound/` salvo indicación. No importa `adapters.outbound` (`pyproject.toml:58-61`) ni `modbus_connection`: solo ve errores de dominio.

## Flows (`flow.py`)

La raíz inyecta `catalog` y `gateway_factory` (`custom_components/modbus_solar/config_flow.py:36-43`).

### `BrandFlow` (`flow.py:49-69`)

Una entry por marca, sin datos de conexión: los equipos son subentries (`flow.py:50`).

- Paso `user`: elige la marca entre `catalog.brands()` (`flow.py:62-64`).
- `unique_id = brand`; si ya existe, aborta con `already_configured` (`flow.py:59-60`).
- `data = {"brand": brand}` y título `BRAND_TITLES[brand]` (`flow.py:61`).
- `async_get_supported_subentry_types` devuelve `{"device": cls.device_flow}` (`flow.py:66-69`).

### `DeviceSubentryFlow` (`flow.py:72-178`)

Alta de un equipo, `async_step_user` (`flow.py:78-117`):

- Campos: `name`, `host`, `port` (por defecto `profile.default_port`), `unit_id` (por defecto `profile.default_unit_id`) y `profile`, filtrado por la marca de la entry (`flow.py:104-111`).
- El duplicado se detecta antes de abrir conexión y aborta con `already_configured` (`flow.py:85-88`).
- Valida con `_probe` (`flow.py:89`, `:167-178`): abre `gateway_factory` y llama a `probe_device`.
- `data = {host, port, unit_id, profile, intervals}` con `DEFAULT_INTERVALS` (`flow.py:94-100`).

Errores del formulario (`flow.py:167-178`):

| Error de dominio | Clave del formulario | Cita |
|---|---|---|
| `EndpointInUse` | `endpoint_in_use` | `flow.py:172-173` |
| `DeviceUnavailable` | `cannot_connect` | `flow.py:174-175` |
| `DeviceProtocolError`, `DecodeError` | `invalid_response` | `flow.py:176-177` |

Reconfigure, `async_step_reconfigure` (`flow.py:119-161`): cambia `host`, `port` e intervalos de los tres tiers.

- Cada intervalo debe ser ≥ `min_tier_interval(profile, tier)`; si no, error `interval_too_short` en el campo del tier (`flow.py:125-128`).
- Recalcula el `unique_id` con el nuevo host y puerto; si choca con otra subentry, aborta con `already_configured` (`flow.py:130-133`).
- Guarda con `async_update_and_abort` (`flow.py:134-143`).

`device_unique_id(host, port, unit_id)` devuelve `f"{host.lower()}:{port}:{unit_id}"` (`flow.py:45-46`).

## `TierCoordinator` (`coordinator.py:21-66`)

`DataUpdateCoordinator[TierResult]`, uno por tier de cada equipo.

- `update_interval = interval_s` (`coordinator.py:40`).
- `always_update: bool = False` se pasa tal cual a `DataUpdateCoordinator` (`coordinator.py:33`, `:41-43`). Con `False` HA solo escribe estado si cambia el `TierResult`. `build_runtime` pone `True` en los tiers con fuentes de energía, para que la integral avance con potencia constante (`runtime.py:67`, `:78`).
- `keys` es el conjunto de claves habilitadas (`coordinator.py:46`).
- `_async_update_data` llama a `read_tier` (`coordinator.py:55`). `DeviceUnavailable` y `DeviceProtocolError` se convierten en `UpdateFailed`, y las entidades del tier pasan a `unavailable` (`coordinator.py:54-60`).
- Guarda `last_error` y `last_error_at` para diagnostics (`coordinator.py:57-58`).
- Los `DecodeError` de `TierResult.decode_errors` se registran con `warning` una vez por clave hasta que se recupera (`coordinator.py:61-65`).
- El log de disponibilidad (`error` al perder el equipo, `info` al recuperarlo) lo hace `DataUpdateCoordinator` (`coordinator.py:59`).

## `DeviceRuntime` (`runtime.py:17-24`)

Estado en memoria de un equipo mientras la entry está cargada: `subentry_id`, `title`, `profile`, `intervals`, `gateway` y `coordinators: dict[PollTier, TierCoordinator]`.

- `build_runtime` mezcla `DEFAULT_INTERVALS` con los de la subentry y crea un coordinator por tier que tenga entidades (`runtime.py:57-90`). Calcula `energy_tiers`, los tiers de las fuentes de energía, y les da `always_update=True` (`runtime.py:66-67`, `:78`).
- `ModbusSolarConfigEntry = ConfigEntry[dict[str, DeviceRuntime]]` es el tipo de `entry.runtime_data` (`runtime.py:27`).
- `enabled_keys` lee el entity registry con `_is_enabled`: una entidad aún no registrada manda `enabled_default` del perfil; una registrada cuenta si no está deshabilitada (`runtime.py:35-41`, `:44-49`). Cada energía habilitada añade sus `sources`, aunque su sensor de potencia esté deshabilitado (`runtime.py:50-53`).

## Entidades (`entities/`)

- `ModbusSolarEntity(CoordinatorEntity[TierCoordinator])` (`entities/base.py:14-41`): acepta `EntitySpec | EnergySpec` (`entities/base.py:18`). `has_entity_name`, `translation_key = spec.key`, `unique_id`, habilitada por defecto según el perfil y `DeviceInfo` del equipo (`entities/base.py:15-36`). `entity_category` solo se aplica a un `EntitySpec`: las energías calculadas son de primer nivel (`entities/base.py:25-27`). Nace `unavailable` hasta la primera lectura correcta (`entities/base.py:38-41`).
- `ModbusSolarSensor` convierte las cadenas de `EntitySpec` a los enums de HA (`entities/factory.py:18-25`). `native_value` sale de `coordinator.data.values` (`entities/factory.py:27-31`).
- `ModbusSolarEnergySensor(ModbusSolarEntity, RestoreSensor)` (`entities/energy.py:14`): kWh, `device_class` `energy`, `state_class` `total_increasing`, precisión 3 (`entities/energy.py:15-18`).
  - `max_gap_s = 3 ×` intervalo del tier: un hueco mayor no se integra (`entities/energy.py:25-26`).
  - Restaura el último total con `async_get_last_sensor_data`; lo que pasa con HA apagado no se integra (`entities/energy.py:29-35`).
  - Muestrea en `_handle_coordinator_update` con `dt_util.utcnow()` (`entities/energy.py:37-43`).
  - Una lectura fallida o una fuente sin valor numérico dan `None` y cortan la serie (`entities/energy.py:45-53`).
  - `native_value` es `total_kwh` del `EnergyAccumulator` (`entities/energy.py:55-57`).
- `build_sensors` devuelve `list[SensorEntity]`: un sensor por `EntitySpec` con `platform is SENSOR` y un `ModbusSolarEnergySensor` por energía, suscrito al coordinator del tier de su primera fuente (`entities/factory.py:34-45`).
- `sensor.py:12-20` obtiene el `id` del dispositivo de marca en el device registry (`sensor.py:15-18`) y añade las entidades de cada equipo con `config_subentry_id` (`sensor.py:19-20`). `build_sensors` y las entidades reciben ese `id` como `brand_device_id`.

## Identificadores

| Qué | Formato | Cita |
|---|---|---|
| `unique_id` de la entry de marca | marca (`ingeteam`) | `flow.py:59` |
| `unique_id` de la subentry | `host.lower():puerto:unidad` | `flow.py:45-46` |
| Dispositivo de equipo | `(DOMAIN, subentry_id)` | `entities/base.py:30` |
| Dispositivo de marca | `(DOMAIN, entry_id)` | `custom_components/modbus_solar/__init__.py:24` |
| `unique_id` de entidad | `f"{subentry_id}_{key}"` | `runtime.py:30-32` |

Cada equipo cuelga del dispositivo de marca con `via_device_id`, el `id` del dispositivo de marca en el device registry y no el `entry_id` (`entities/base.py:34-35`). HA 2026.9 deprecia `via_device` y lo retira en 2027.8.0. El `subentry_id` es un ULID: cambiar el host en reconfigure no duplica entidades (`runtime.py:31`).

## Diagnostics (`diagnostics.py`, `custom_components/modbus_solar/diagnostics.py`)

`device_diagnostics(runtime, subentry_data)` devuelve (`diagnostics.py:14-43`):

- `profile` (id) e `intervals` (`diagnostics.py:39-40`);
- por tier: `last_update_success`, `last_error` y `last_error_at` (`diagnostics.py:15-22`);
- por entidad del perfil: `address`, `dtype`, `word_order`, `scale`, `raw` y `value` (`diagnostics.py:24`, `:29-36`). Las energías calculadas no salen: no tienen registro. Usa el último `TierResult` correcto, también tras un fallo (`diagnostics.py:25`);
- `subentry` con `host` oculto mediante `async_redact_data` (`diagnostics.py:11`, `:38`).

La raíz delega: `async_get_config_entry_diagnostics` agrega todos los equipos de la marca (`custom_components/modbus_solar/diagnostics.py:13-19`) y `async_get_device_diagnostics` devuelve el del equipo, o `{}` para el dispositivo de marca (`custom_components/modbus_solar/diagnostics.py:22-29`).

Uso: verificar en la VM los supuestos de escala y `word_order` del perfil `ingeteam.oneplay` (`custom_components/modbus_solar/profiles/ingeteam/oneplay.py:32`, `:43`).
