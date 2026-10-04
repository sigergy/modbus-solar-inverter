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

## `TierCoordinator` (`coordinator.py:21-64`)

`DataUpdateCoordinator[TierResult]`, uno por tier de cada equipo.

- `update_interval = interval_s` y `always_update=False` (`coordinator.py:39-41`).
- `keys` es el conjunto de claves habilitadas (`coordinator.py:44`).
- `_async_update_data` llama a `read_tier` (`coordinator.py:53`). `DeviceUnavailable` y `DeviceProtocolError` se convierten en `UpdateFailed`, y las entidades del tier pasan a `unavailable` (`coordinator.py:54-58`).
- Guarda `last_error` y `last_error_at` para diagnostics (`coordinator.py:55-56`).
- Los `DecodeError` de `TierResult.decode_errors` se registran con `warning` una vez por clave hasta que se recupera (`coordinator.py:59-63`).
- El log de disponibilidad (`error` al perder el equipo, `info` al recuperarlo) lo hace `DataUpdateCoordinator` (`coordinator.py:57`).

## `DeviceRuntime` (`runtime.py:17-24`)

Estado en memoria de un equipo mientras la entry está cargada: `subentry_id`, `title`, `profile`, `intervals`, `gateway` y `coordinators: dict[PollTier, TierCoordinator]`.

- `build_runtime` mezcla `DEFAULT_INTERVALS` con los de la subentry y crea un coordinator por tier que tenga entidades (`runtime.py:48-78`).
- `ModbusSolarConfigEntry = ConfigEntry[dict[str, DeviceRuntime]]` es el tipo de `entry.runtime_data` (`runtime.py:27`).
- `enabled_keys` lee el entity registry: una entidad aún no registrada manda `enabled_default` del perfil; una registrada cuenta si no está deshabilitada (`runtime.py:35-45`).

## Entidades (`entities/`)

- `ModbusSolarEntity(CoordinatorEntity[TierCoordinator])` (`entities/base.py:13-39`): `has_entity_name`, `translation_key = spec.key`, `unique_id`, habilitada por defecto según el perfil y `DeviceInfo` del equipo (`entities/base.py:14-34`). Nace `unavailable` hasta la primera lectura correcta (`entities/base.py:36-39`).
- `ModbusSolarSensor` convierte las cadenas de `EntitySpec` a los enums de HA (`entities/factory.py:17-24`). `native_value` sale de `coordinator.data.values` (`entities/factory.py:26-30`).
- `build_sensors` crea un sensor por `EntitySpec` con `platform is SENSOR` (`entities/factory.py:33-38`).
- `sensor.py:12-20` obtiene el `id` del dispositivo de marca en el device registry (`sensor.py:15-18`) y añade las entidades de cada equipo con `config_subentry_id` (`sensor.py:19-20`). `build_sensors` y las entidades reciben ese `id` como `brand_device_id`.

## Identificadores

| Qué | Formato | Cita |
|---|---|---|
| `unique_id` de la entry de marca | marca (`ingeteam`) | `flow.py:59` |
| `unique_id` de la subentry | `host.lower():puerto:unidad` | `flow.py:45-46` |
| Dispositivo de equipo | `(DOMAIN, subentry_id)` | `entities/base.py:28` |
| Dispositivo de marca | `(DOMAIN, entry_id)` | `custom_components/modbus_solar/__init__.py:24` |
| `unique_id` de entidad | `f"{subentry_id}_{key}"` | `runtime.py:30-32` |

Cada equipo cuelga del dispositivo de marca con `via_device_id`, el `id` del dispositivo de marca en el device registry y no el `entry_id` (`entities/base.py:32-33`). HA 2026.9 deprecia `via_device` y lo retira en 2027.8.0. El `subentry_id` es un ULID: cambiar el host en reconfigure no duplica entidades (`runtime.py:31`).

## Diagnostics (`diagnostics.py`, `custom_components/modbus_solar/diagnostics.py`)

`device_diagnostics(runtime, subentry_data)` devuelve (`diagnostics.py:14-43`):

- `profile` (id) e `intervals` (`diagnostics.py:39-40`);
- por tier: `last_update_success`, `last_error` y `last_error_at` (`diagnostics.py:15-22`);
- por entidad: `address`, `dtype`, `word_order`, `scale`, `raw` y `value` (`diagnostics.py:29-36`). Usa el último `TierResult` correcto, también tras un fallo (`diagnostics.py:25`);
- `subentry` con `host` oculto mediante `async_redact_data` (`diagnostics.py:11`, `:38`).

La raíz delega: `async_get_config_entry_diagnostics` agrega todos los equipos de la marca (`custom_components/modbus_solar/diagnostics.py:13-19`) y `async_get_device_diagnostics` devuelve el del equipo, o `{}` para el dispositivo de marca (`custom_components/modbus_solar/diagnostics.py:22-29`).

Uso: verificar en la VM los supuestos de escala y `word_order` del perfil (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:32`, `:43`).
