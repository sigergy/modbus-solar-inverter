# Arquitectura: adaptadores de entrada

Documento vivo. Todo lo que habla con Home Assistant. Rutas bajo `custom_components/modbus_solar/adapters/inbound/` salvo indicación. No importa `adapters.outbound` (`pyproject.toml:58-61`) ni `modbus_connection`: solo ve errores de dominio.

## Flow (`flow.py`)

La raíz inyecta `catalog` y `gateway_factory` (`custom_components/modbus_solar/config_flow.py:36-38`).

### `DeviceConfigFlow` (`flow.py:291-759`)

Una config entry por equipo (ADR [0010](../../decisions/0010-entry-per-device.md)). `VERSION = 2` (`flow.py:294`). Detalle de pantallas y textos en [features/device-setup](../../features/device-setup.md).

Alta, en este orden:

- Paso `user`: `SelectSelector` en modo lista con una opción por marca (`flow.py:311-317`).
- Paso `model`: un perfil por opción; la opción es el id sin puntos, válido como `translation_key` (`flow.py:94-96`, `:319-341`). Al entrar olvida la sonda y los componentes (`flow.py:325-327`).
- Paso `connection`: `host` y una sección plegada `advanced` con `port` y `unit_id`, por defecto `profile.default_port` y `profile.default_unit_id` (`flow.py:381-438`).
  - El duplicado se detecta antes de abrir conexión y aborta con `already_configured` (`flow.py:390-391`).
  - Valida con `_try_probe` (`flow.py:368-379`, `:392`): abre `gateway_factory` y llama a `probe_device`, todo dentro de `asyncio.timeout(PROBE_TIMEOUT_S)`, 20 s (`flow.py:61`, `:756-759`).
  - Con error, vuelve el formulario con lo escrito y un selector de modelo para corregirlo; los puertos del modelo nuevo solo se aplican si no se tocaron (`flow.py:343-358`, `:407-409`).
  - Con componentes opcionales sigue a `components`; sin ellos, a `readings` (`flow.py:398-401`).
- Paso `components`: selector múltiple con los componentes opcionales del perfil; por defecto, los marcados `default`, o lo ya elegido al volver atrás (`flow.py:440-466`).
- Paso `readings`: menú con las lecturas de la sonda de los componentes elegidos y tres salidas, `name`, `model` y `connection` (`flow.py:468-480`).
- Paso `name`: nombre, Device ID y número de serie (`flow.py:482-535`).
  - El Device ID propuesto es el menor entero libre entre las entries del mismo `device_type` (`flow.py:73-91`, `:488`). Uno repetido da `device_id_in_use` (`flow.py:493-494`).
  - Un número de serie escrito solo admite letras y números ASCII; si no, `invalid_serial_number` (`flow.py:68-70`, `:495-496`).
  - Manda el serie escrito; si está vacío, el leído por la sonda; si no hay ninguno, no se guarda (`flow.py:498-501`).
- Paso `intervals`: un campo por tier con entidades (`flow.py:564-589`). Crea la entry con `title = name` y `data = {host, port, unit_id, profile, components, intervals, device_id, serial_number}`; `device_id` y `serial_number` solo si existen (`flow.py:575-586`). Los tiers sin entidades conservan `DEFAULT_INTERVALS` (`flow.py:579-580`).

Errores del formulario de conexión (`flow.py:368-379`):

| Error de dominio | Clave del formulario | Cita |
|---|---|---|
| `EndpointInUse` | `endpoint_in_use` | `flow.py:374-375` |
| `DeviceUnavailable`, `TimeoutError` | `cannot_connect` | `flow.py:376-377` |
| `DeviceProtocolError`, `DecodeError` | `invalid_response` | `flow.py:378-379` |

Funciones auxiliares:

- `format_readings(profile, selection, result, translations, language)` (`flow.py:107-142`) escribe las lecturas de la sonda agrupadas por componente: un título por dispositivo y una línea `- {nombre}: {valor} {unidad}` por sensor de la selección que la sonda leyó. Los `binary_sensor` no salen (`flow.py:122-123`). Nombre y estado del enum salen de `component.modbus_solar.entity.sensor.<key>`; sin traducción, la clave. `None` se muestra como `—`. Los números llevan separador de miles según el idioma (`format_number`, `flow.py:99-104`).
- `present_tiers(selection)` da los tiers con entidades de los componentes elegidos, en el orden de `PollTier` (`flow.py:150-152`).
- `entity_list(profile, selection, tier, translations)` lista las entidades de un tier con su dispositivo: leídas, energías calculadas y controles; las desactivadas por defecto llevan una marca (`flow.py:155-193`).
- `intervals_schema` y `intervals_placeholders` construyen el formulario de intervalos: una sección plegada por tier, con el mínimo y la lista de entidades en la descripción (`flow.py:196-217`). Los comparten el alta y reconfigure por `_show_intervals` (`flow.py:537-562`).
- `check_intervals(profile, tiers, user_input)` valida primero cada intervalo contra `min_tier_interval(profile, tier)` (`interval_too_short` en el campo del tier) y, solo sin errores, el presupuesto: si `request_rate` supera 1 petición por segundo, `interval_budget_exceeded` en `base` (`flow.py:220-231`, `:147`). ADR [0016](../../decisions/0016-instant-tier.md).

Reconfigure, cuatro pasos (`flow.py:591-754`):

- `reconfigure`: `host`, número de serie, Device ID y la sección `advanced` con `port` y `unit_id`. Recalcula el `unique_id`; si choca con otra entry, aborta con `already_configured` (`flow.py:597-603`). Valida Device ID y serie como el alta, con el propio Device ID excluido (`flow.py:604-612`), y abre la sonda (`flow.py:614`). Una entry sin Device ID lo deja opcional (`flow.py:669-674`). El serie escrito manda; si está vacío, el leído; si no hay ninguno, la clave desaparece (`flow.py:621-622`).
- `reconfigure_components`: solo con componentes opcionales; parte de los guardados, o de todos si la entry no tiene la clave (`flow.py:676-686`).
- `reconfigure_intervals`: mismos campos y comprobaciones que el alta, con los intervalos guardados por defecto (`flow.py:688-727`). Guarda `components`, `intervals`, `device_id` y `serial_number` y recarga con `async_update_reload_and_abort` (`flow.py:700-717`). No hay update listener.
- `reconfigure_rename`: solo si el Device ID cambia (`flow.py:712-715`). `plan_rename` calcula qué `entity_id` llevan el prefijo generado con el ID viejo; renombra los que no chocan con otra entidad y deja los demás (`flow.py:252-288`, `:729-754`).

`device_unique_id(host, port, unit_id)` devuelve `f"{host.lower()}:{port}:{unit_id}"` (`flow.py:64-65`).

## `TierCoordinator` (`coordinator.py:21-66`)

`DataUpdateCoordinator[TierResult]`, uno por tier de cada equipo.

- `update_interval = interval_s` (`coordinator.py:40`).
- `always_update: bool = False` se pasa tal cual a `DataUpdateCoordinator` (`coordinator.py:33`, `:41-43`). Con `False` HA solo escribe estado si cambia el `TierResult`. `build_runtime` pone `True` en los tiers con fuentes de energía, para que la integral avance con potencia constante (`runtime.py:78-79`, `:90`).
- `keys` es el conjunto de claves habilitadas (`coordinator.py:46`).
- `_async_update_data` llama a `read_tier` (`coordinator.py:55`). `DeviceUnavailable` y `DeviceProtocolError` se convierten en `UpdateFailed`, y las entidades del tier pasan a `unavailable` (`coordinator.py:54-60`).
- Guarda `last_error` y `last_error_at` para diagnostics (`coordinator.py:57-58`).
- Los `DecodeError` de `TierResult.decode_errors` se registran con `warning` una vez por clave hasta que se recupera (`coordinator.py:61-65`).
- El log de disponibilidad (`error` al perder el equipo, `info` al recuperarlo) lo hace `DataUpdateCoordinator` (`coordinator.py:59`).

## `DeviceRuntime` (`runtime.py:19-31`)

Estado en memoria del equipo mientras su entry está cargada: `entry_id`, `title`, `profile`, `selection`, `intervals`, `gateway`, `writer`, `coordinators: dict[PollTier, TierCoordinator]`, `control_states: dict[str, GatedState]`, `device_id` y `serial_number`.

- `selection` es lo elegido en el alta y manda sobre `profile.entities` (`runtime.py:24`). La calcula la raíz con `select(profile, chosen)` (`custom_components/modbus_solar/__init__.py:62-64`). Ver [application](../application.md).
- `build_runtime` mezcla `DEFAULT_INTERVALS` con los de `entry.data` y crea un coordinator por tier que tenga entidades de la selección (`runtime.py:65-94`). `DEFAULT_INTERVALS` completa los tiers ausentes en entries anteriores (`runtime.py:76-77`). Calcula `energy_tiers`, los tiers de las fuentes de energía, y les da `always_update=True` (`runtime.py:78-79`, `:90`). Sin selección usa todos los componentes opcionales (`runtime.py:74-75`). Recibe `gateway` y `writer` por separado, aunque la raíz pasa el mismo objeto (`runtime.py:69-70`).
- `control_states` tiene un `GatedState` por control de la selección, con `limit = control.default`. Lo comparten el number y el switch del mismo control (`runtime.py:104-105`).
- `device_id` y `serial_number` salen de `entry.data` (`runtime.py:106-107`); `None` si la entry no los tiene.
- `ModbusSolarConfigEntry = ConfigEntry[DeviceRuntime]` es el tipo de `entry.runtime_data` (`runtime.py:34`).
- `enabled_keys` lee el entity registry con `_is_enabled`: una entidad aún no registrada manda `enabled_default` del perfil; una registrada cuenta si no está deshabilitada (`runtime.py:42-48`, `:51-62`). Cada energía habilitada añade sus `sources`, aunque su sensor de potencia esté deshabilitado (`runtime.py:58-61`).

La raíz, antes de crear el runtime, borra del registro las entidades y los dispositivos de los componentes que ya no están elegidos (`_remove_unselected`, `custom_components/modbus_solar/__init__.py:28-53`, llamada en `:65`). ADR [0015](../../decisions/0015-device-per-component.md).

## Entidades (`entities/`)

- `device_info(entry_id, profile, component, serial)` (`entities/base.py:16-35`) da el dispositivo de un componente. El principal usa el identificador `(DOMAIN, entry_id)` y lleva el número de serie; el resto usa `(DOMAIN, f"{entry_id}_{componente}")` y cuelga del principal con `via_device` (`entities/base.py:25`, `:30-34`). El nombre sale de `translation_key` = `{clave}` y no lleva el Device ID (`entities/base.py:26`).
- `ModbusSolarEntity(CoordinatorEntity[TierCoordinator])` (`entities/base.py:38-77`): acepta `EntitySpec | EnergySpec | GatedLimitSpec` y una `key` opcional (`entities/base.py:41-51`): un control da dos entidades, number y switch, y la clave la elige quien construye. `has_entity_name`, `translation_key = key`, `unique_id`, habilitada por defecto según el perfil y el `DeviceInfo` del componente de la entidad (`entities/base.py:52-59`). `entity_category` solo se aplica a un `EntitySpec`: las energías calculadas son de primer nivel (`entities/base.py:55-57`). `suggested_object_id` pone el Device ID delante del nombre de la entidad; HA antepone el nombre del dispositivo y el `entity_id` queda `sensor.bateria_0_tension`. Solo cuenta en el alta en el registro, y casa con el prefijo de `device_label` del renombrado (`entities/base.py:61-72`, `flow.py:243-249`). Nace `unavailable` hasta la primera lectura correcta (`entities/base.py:74-77`).
- `ModbusSolarSensor` convierte las cadenas de `EntitySpec` a los enums de HA (`entities/factory.py:19-29`). `native_value` sale de `coordinator.data.values` (`entities/factory.py:31-35`).
- `ModbusSolarBinarySensor` (`entities/binary_sensor.py:11-23`): `is_on` es el `bool` ya decodificado del bit; `None` sin datos o sin valor (`entities/binary_sensor.py:18-23`). Los 14 bits del STORAGE son diagnóstico y vienen habilitados.
- `ModbusSolarEnergySensor(ModbusSolarEntity, RestoreSensor)` (`entities/energy.py:14`): kWh, `device_class` `energy`, `state_class` `total_increasing`, precisión 3 (`entities/energy.py:15-18`).
  - `max_gap_s = 3 ×` intervalo del tier: un hueco mayor no se integra (`entities/energy.py:23-25`).
  - Restaura el último total con `async_get_last_sensor_data`; lo que pasa con HA apagado no se integra (`entities/energy.py:27-33`).
  - Muestrea en `_handle_coordinator_update` con `dt_util.utcnow()` (`entities/energy.py:35-41`).
  - Una lectura fallida o una fuente sin valor numérico dan `None` y cortan la serie (`entities/energy.py:43-51`).
  - `native_value` es `total_kwh` del `EnergyAccumulator` (`entities/energy.py:53-55`).
- `build_sensors` devuelve `list[SensorEntity]`: un sensor por `EntitySpec` de la selección con `platform is SENSOR` y un `ModbusSolarEnergySensor` por energía de la selección, suscrito al coordinator del tier de su primera fuente (`entities/factory.py:38-49`). `build_binary_sensors` hace lo mismo con `platform is BINARY_SENSOR` (`entities/factory.py:52-57`).
- `ModbusSolarControl(ModbusSolarEntity)` (`entities/control.py:27-33`) es la base del number y del switch de un control. Guarda el `GatedLimitSpec` (`:30`), el `writer` del runtime (`:31`) y el `GatedState` compartido, `runtime.control_states[spec.key]` (`:33`).
  - `write_errors()` (`entities/control.py:16-24`) traduce `DeviceUnavailable`, `DeviceProtocolError` y `EncodeError` a `HomeAssistantError` con `translation_key = write_failed` y el error como placeholder.
- `ModbusSolarNumber(ModbusSolarControl, RestoreNumber)` (`entities/number.py:12`): modo `BOX` (`:13`); mínimo, máximo, paso, unidad y clase salen del `GatedLimitSpec` (`:17-22`).
  - Al añadirse restaura el último valor si está dentro del rango del control y no escribe nada al equipo (`entities/number.py:24-30`).
  - `native_value` es `state.limit` (`entities/number.py:32-34`). `async_set_native_value` llama a `set_limit` dentro de `write_errors` y después escribe el estado (`entities/number.py:36-39`).
- `ModbusSolarSwitch(ModbusSolarControl, SwitchEntity, RestoreEntity)` (`entities/switch.py:16`): usa `spec.switch_key` (`:21`) y `assumed_state = True` porque el equipo no permite leer el ajuste (`:17-18`).
  - Al añadirse restaura `on` u `off` sin escribir al equipo (`entities/switch.py:23-28`). `is_on` es `state.enabled` (`:30-32`).
  - `turn_on` y `turn_off` llaman a `set_enabled` dentro de `write_errors` y después escriben el estado (`entities/switch.py:34-43`).
- `build_numbers` y `build_switches` crean un number y un switch por control de la selección (`entities/factory.py:66-73`). Los dos cuelgan del coordinator del tier de `probe_key` (`entities/factory.py:60-63`): hasta la primera lectura correcta de ese tier, o con el equipo caído, quedan `unavailable`. Ver [features/control](../../features/control.md) y ADR [0012](../../decisions/0012-optimistic-restored-state.md).
- `sensor.py:10-13`, `binary_sensor.py:10-13`, `number.py:10-13` y `switch.py:10-13` añaden las entidades de la entry con `build_sensors`, `build_binary_sensors`, `build_numbers` y `build_switches` sobre `entry.runtime_data`. La lista `PLATFORMS` está en `custom_components/modbus_solar/__init__.py:25`.

## Identificadores

| Qué | Formato | Cita |
|---|---|---|
| `unique_id` de la entry | `host.lower():puerto:unidad` | `flow.py:64-65` |
| Dispositivo principal | `(DOMAIN, entry_id)` | `entities/base.py:25` |
| Dispositivo de un componente | `(DOMAIN, f"{entry_id}_{componente}")`, con `via_device` al principal | `entities/base.py:25`, `:34` |
| `unique_id` de entidad | `f"{entry_id}_{key}"` | `runtime.py:37-39` |

Un dispositivo por componente elegido (ADR [0015](../../decisions/0015-device-per-component.md)). El `entry_id` es un ULID: cambiar el host en reconfigure no duplica entidades ni dispositivos (`runtime.py:38`). El Device ID va en el `entity_id` de las entidades nuevas, no en el nombre del dispositivo; no entra en ningún identificador.

## Diagnostics (`diagnostics.py`, `custom_components/modbus_solar/diagnostics.py`)

`device_diagnostics(runtime, entry_data)` devuelve (`diagnostics.py:15-44`):

- `profile` (id) e `intervals` (`diagnostics.py:40-41`);
- por tier: `last_update_success`, `last_error` y `last_error_at` (`diagnostics.py:16-23`);
- por entidad de la selección: `address`, `dtype`, `word_order`, `scale`, `raw` y `value` (`diagnostics.py:24-37`). Las energías calculadas no salen: no tienen registro. Usa el último `TierResult` correcto, también tras un fallo (`diagnostics.py:26`);
- `entry` con los datos de la entry y `host` y `serial_number` ocultos mediante `async_redact_data` (`diagnostics.py:12`, `:39`).

La raíz delega: `async_get_config_entry_diagnostics` y `async_get_device_diagnostics` devuelven lo mismo, el diagnostics del equipo de la entry (`custom_components/modbus_solar/diagnostics.py:12-19`).

Uso: verificar en la VM los supuestos de escala y `word_order` de los perfiles.
