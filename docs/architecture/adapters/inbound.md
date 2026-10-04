# Arquitectura: adaptadores de entrada

Documento vivo. Todo lo que habla con Home Assistant. Rutas bajo `custom_components/modbus_solar/adapters/inbound/` salvo indicación. No importa `adapters.outbound` (`pyproject.toml:58-61`) ni `modbus_connection`: solo ve errores de dominio.

## Flow (`flow.py`)

La raíz inyecta `catalog` y `gateway_factory` (`custom_components/modbus_solar/config_flow.py:36-38`).

### `DeviceConfigFlow` (`flow.py:73-205`)

Una config entry por equipo (ADR [0010](../../decisions/0010-entry-per-device.md)). `VERSION = 2` (`flow.py:76`).

- Paso `user`: `SelectSelector` en modo lista con un perfil por opción, etiqueta `"{marca} · {modelos}"` (`flow.py:84-94`).
- Paso `connection`: `host` y una sección plegada `advanced` con `port` y `unit_id`, por defecto `profile.default_port` y `profile.default_unit_id` (`flow.py:96-137`).
  - El duplicado se detecta antes de abrir conexión y aborta con `already_configured` (`flow.py:104-105`).
  - Valida con `_probe` (`flow.py:107`, `:202-205`): abre `gateway_factory` y llama a `probe_device`, todo dentro de `asyncio.timeout(PROBE_TIMEOUT_S)`, 20 s (`flow.py:48`).
  - Con error, vuelve el formulario con lo escrito (`flow.py:133-137`).
- Paso `confirm`: placeholders `host` y `readings`, campo `name` con `"{marca} {primer modelo}"` por defecto (`flow.py:139-155`). Crea la entry con `title = name` y `data = {host, port, unit_id, profile, intervals}`, con `DEFAULT_INTERVALS` (`flow.py:142-149`).

Errores del formulario (`flow.py:106-113`):

| Error de dominio | Clave del formulario | Cita |
|---|---|---|
| `EndpointInUse` | `endpoint_in_use` | `flow.py:108-109` |
| `DeviceUnavailable`, `TimeoutError` | `cannot_connect` | `flow.py:110-111` |
| `DeviceProtocolError`, `DecodeError` | `invalid_response` | `flow.py:112-113` |

`format_readings(profile, result, translations)` (`flow.py:55-70`) escribe las lecturas de la sonda: una línea `- {nombre}: {valor}` por clave de `result.values`, en el orden del perfil. Nombre y estado del enum salen de `component.modbus_solar.entity.sensor.<key>`; sin traducción, la clave. `None` se muestra como `—`. Las traducciones las pide el flow con `async_get_translations` (`flow.py:116`).

Reconfigure, `async_step_reconfigure` (`flow.py:157-200`): cambia `host`, `port` e intervalos de los tres tiers.

- Cada intervalo debe ser ≥ `min_tier_interval(profile, tier)`; si no, error `interval_too_short` en el campo del tier (`flow.py:163-165`).
- Recalcula el `unique_id` con el nuevo host y puerto; si choca con otra entry, aborta con `already_configured` (`flow.py:167-172`).
- Guarda y recarga con `async_update_reload_and_abort` (`flow.py:174-182`). No hay update listener.

`device_unique_id(host, port, unit_id)` devuelve `f"{host.lower()}:{port}:{unit_id}"` (`flow.py:51-52`).

## `TierCoordinator` (`coordinator.py:21-66`)

`DataUpdateCoordinator[TierResult]`, uno por tier de cada equipo.

- `update_interval = interval_s` (`coordinator.py:40`).
- `always_update: bool = False` se pasa tal cual a `DataUpdateCoordinator` (`coordinator.py:33`, `:41-43`). Con `False` HA solo escribe estado si cambia el `TierResult`. `build_runtime` pone `True` en los tiers con fuentes de energía, para que la integral avance con potencia constante (`runtime.py:66`, `:77`).
- `keys` es el conjunto de claves habilitadas (`coordinator.py:46`).
- `_async_update_data` llama a `read_tier` (`coordinator.py:55`). `DeviceUnavailable` y `DeviceProtocolError` se convierten en `UpdateFailed`, y las entidades del tier pasan a `unavailable` (`coordinator.py:54-60`).
- Guarda `last_error` y `last_error_at` para diagnostics (`coordinator.py:57-58`).
- Los `DecodeError` de `TierResult.decode_errors` se registran con `warning` una vez por clave hasta que se recupera (`coordinator.py:61-65`).
- El log de disponibilidad (`error` al perder el equipo, `info` al recuperarlo) lo hace `DataUpdateCoordinator` (`coordinator.py:59`).

## `DeviceRuntime` (`runtime.py:17-24`)

Estado en memoria del equipo mientras su entry está cargada: `entry_id`, `title`, `profile`, `intervals`, `gateway` y `coordinators: dict[PollTier, TierCoordinator]`.

- `build_runtime` mezcla `DEFAULT_INTERVALS` con los de `entry.data` y crea un coordinator por tier que tenga entidades (`runtime.py:57-89`). Calcula `energy_tiers`, los tiers de las fuentes de energía, y les da `always_update=True` (`runtime.py:65-66`, `:77`).
- `ModbusSolarConfigEntry = ConfigEntry[DeviceRuntime]` es el tipo de `entry.runtime_data` (`runtime.py:27`).
- `enabled_keys` lee el entity registry con `_is_enabled`: una entidad aún no registrada manda `enabled_default` del perfil; una registrada cuenta si no está deshabilitada (`runtime.py:35-41`, `:44-49`). Cada energía habilitada añade sus `sources`, aunque su sensor de potencia esté deshabilitado (`runtime.py:50-53`).

## Entidades (`entities/`)

- `ModbusSolarEntity(CoordinatorEntity[TierCoordinator])` (`entities/base.py:14-37`): acepta `EntitySpec | EnergySpec` (`entities/base.py:17`). `has_entity_name`, `translation_key = spec.key`, `unique_id`, habilitada por defecto según el perfil y `DeviceInfo` del equipo (`entities/base.py:15-32`). `entity_category` solo se aplica a un `EntitySpec`: las energías calculadas son de primer nivel (`entities/base.py:23-25`). Nace `unavailable` hasta la primera lectura correcta (`entities/base.py:34-37`).
- `ModbusSolarSensor` convierte las cadenas de `EntitySpec` a los enums de HA (`entities/factory.py:16-23`). `native_value` sale de `coordinator.data.values` (`entities/factory.py:25-29`).
- `ModbusSolarEnergySensor(ModbusSolarEntity, RestoreSensor)` (`entities/energy.py:14`): kWh, `device_class` `energy`, `state_class` `total_increasing`, precisión 3 (`entities/energy.py:15-18`).
  - `max_gap_s = 3 ×` intervalo del tier: un hueco mayor no se integra (`entities/energy.py:23-24`).
  - Restaura el último total con `async_get_last_sensor_data`; lo que pasa con HA apagado no se integra (`entities/energy.py:27-33`).
  - Muestrea en `_handle_coordinator_update` con `dt_util.utcnow()` (`entities/energy.py:35-41`).
  - Una lectura fallida o una fuente sin valor numérico dan `None` y cortan la serie (`entities/energy.py:43-51`).
  - `native_value` es `total_kwh` del `EnergyAccumulator` (`entities/energy.py:53-55`).
- `build_sensors` devuelve `list[SensorEntity]`: un sensor por `EntitySpec` con `platform is SENSOR` y un `ModbusSolarEnergySensor` por energía, suscrito al coordinator del tier de su primera fuente (`entities/factory.py:32-43`).
- `sensor.py:10-13` añade las entidades del equipo de la entry con `build_sensors(entry.runtime_data)`.

## Identificadores

| Qué | Formato | Cita |
|---|---|---|
| `unique_id` de la entry | `host.lower():puerto:unidad` | `flow.py:51-52` |
| Dispositivo del equipo | `(DOMAIN, entry_id)` | `entities/base.py:28` |
| `unique_id` de entidad | `f"{entry_id}_{key}"` | `runtime.py:30-32` |

Un único dispositivo por entry, sin `via_device_id`. El `entry_id` es un ULID: cambiar el host en reconfigure no duplica entidades (`runtime.py:31`).

## Diagnostics (`diagnostics.py`, `custom_components/modbus_solar/diagnostics.py`)

`device_diagnostics(runtime, entry_data)` devuelve (`diagnostics.py:14-43`):

- `profile` (id) e `intervals` (`diagnostics.py:39-40`);
- por tier: `last_update_success`, `last_error` y `last_error_at` (`diagnostics.py:15-22`);
- por entidad del perfil: `address`, `dtype`, `word_order`, `scale`, `raw` y `value` (`diagnostics.py:24`, `:29-36`). Las energías calculadas no salen: no tienen registro. Usa el último `TierResult` correcto, también tras un fallo (`diagnostics.py:25`);
- `entry` con los datos de la entry y `host` oculto mediante `async_redact_data` (`diagnostics.py:11`, `:38`).

La raíz delega: `async_get_config_entry_diagnostics` y `async_get_device_diagnostics` devuelven lo mismo, el diagnostics del equipo de la entry (`custom_components/modbus_solar/diagnostics.py:12-19`).

Uso: verificar en la VM los supuestos de escala y `word_order` del perfil `ingeteam.oneplay` (`custom_components/modbus_solar/profiles/ingeteam/oneplay.py:32`, `:43`).
