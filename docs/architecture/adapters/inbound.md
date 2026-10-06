# Arquitectura: adaptadores de entrada

Documento vivo. Todo lo que habla con Home Assistant. Rutas bajo `custom_components/modbus_solar/adapters/inbound/` salvo indicación. No importa `adapters.outbound` (`pyproject.toml:58-61`) ni `modbus_connection`: solo ve errores de dominio.

## Flow (`flow.py`)

La raíz inyecta `catalog` y `gateway_factory` (`custom_components/modbus_solar/config_flow.py:36-38`).

### `DeviceConfigFlow` (`flow.py:305-867`)

Una config entry por equipo (ADR [0010](../../decisions/0010-entry-per-device.md)). `VERSION = 2` (`flow.py:308`). Detalle de pantallas y textos en [features/device-setup](../../features/device-setup.md).

Alta, en este orden:

- Paso `user`: `SelectSelector` en modo lista con una opción por marca (`flow.py:327-333`).
- Paso `model`: un perfil por opción; la opción es el id sin puntos, válido como `translation_key` (`flow.py:95-97`, `:335-358`). Al entrar olvida la sonda, los componentes y el modo de medición (`flow.py:341-344`).
- Paso `connection`: `host` y una sección plegada `advanced` con `port` y `unit_id`, por defecto `profile.default_port` y `profile.default_unit_id` (`flow.py:399-458`).
  - El duplicado se detecta antes de abrir conexión y aborta con `already_configured` (`flow.py:408-409`).
  - Valida con `_try_probe` (`flow.py:386-397`, `:410`): abre `gateway_factory` y llama a `probe_device`, todo dentro de `asyncio.timeout(PROBE_TIMEOUT_S)`, 20 s (`flow.py:62`, `:864-867`).
  - Con error, vuelve el formulario con lo escrito y un selector de modelo para corregirlo; los puertos del modelo nuevo solo se aplican si no se tocaron. Cambiar de modelo olvida componentes y modo de medición (`_switch_profile`, `flow.py:360-376`, `:371-373`, `:427-429`).
  - Con modos de medición sigue a `metering`; si no, con componentes opcionales a `components`, y sin ellos a `readings` (`flow.py:416-421`).
- Paso `metering`: desplegable `SelectSelector` con los modos del perfil y `translation_key = metering_mode`; por defecto, lo ya elegido o el primer modo (`flow.py:460-468`, `_show_metering` en `:470-483`). Sigue a `components` o a `readings` (`flow.py:463-467`). ADR [0017](../../decisions/0017-metering-mode.md).
- Paso `components`: selector múltiple con los componentes opcionales del perfil; por defecto, los marcados `default`, o lo ya elegido al volver atrás (`flow.py:485-539`). `_show_components` marca además el vatímetro del modo, `required_component` (`flow.py:512-517`). Si el usuario lo desmarca, `missing_meter` da el error `metering_component_required` con los placeholders `component` y `mode` (`flow.py:242-245`, `:489-492`, `:528-533`).
- Paso `readings`: menú con las lecturas de la sonda de los componentes elegidos y tres salidas, `name`, `model` y `connection` (`flow.py:541-553`).
- Paso `name`: nombre, Device ID y número de serie (`flow.py:555-608`).
  - El Device ID propuesto es el menor entero libre entre las entries del mismo `device_type` (`flow.py:74-92`, `:561`). Uno repetido da `device_id_in_use` (`flow.py:566-567`).
  - Un número de serie escrito solo admite letras y números ASCII; si no, `invalid_serial_number` (`flow.py:69-71`, `:568-569`).
  - Manda el serie escrito; si está vacío, el leído por la sonda; si no hay ninguno, no se guarda (`flow.py:571-574`).
- Paso `intervals`: un campo por tier con entidades (`flow.py:638-673`). Crea la entry con `title = name` y `data = {host, port, unit_id, profile, components, intervals, metering, device_id, serial_number}`; `metering` solo si el perfil tiene modos, y `device_id` y `serial_number` solo si existen (`flow.py:649-663`, `:656-658`). Los tiers sin entidades conservan `DEFAULT_INTERVALS` (`flow.py:653-654`).

Errores del formulario de conexión (`flow.py:386-397`):

| Error de dominio | Clave del formulario | Cita |
|---|---|---|
| `EndpointInUse` | `endpoint_in_use` | `flow.py:392-393` |
| `DeviceUnavailable`, `TimeoutError` | `cannot_connect` | `flow.py:394-395` |
| `DeviceProtocolError`, `DecodeError` | `invalid_response` | `flow.py:396-397` |

Funciones auxiliares:

- `format_readings(profile, selection, result, translations, language)` (`flow.py:108-143`) escribe las lecturas de la sonda agrupadas por componente: un título por dispositivo y una línea `- {nombre}: {valor} {unidad}` por sensor de la selección que la sonda leyó. Los `binary_sensor` no salen (`flow.py:123-124`). Nombre y estado del enum salen de `component.modbus_solar.entity.sensor.<key>`; sin traducción, la clave. `None` se muestra como `—`. Los números llevan separador de miles según el idioma (`format_number`, `flow.py:100-105`).
- `present_tiers(selection)` da los tiers con entidades de los componentes elegidos, en el orden de `PollTier` (`flow.py:151-153`).
- `entity_list(profile, selection, tier, translations)` lista las entidades de un tier con su dispositivo: leídas, potencias y energías calculadas y controles; las desactivadas por defecto llevan una marca. Los dispositivos de los modos (Generador) van detrás de los opcionales (`flow.py:156-201`, `:159-164`).
- `intervals_schema` y `intervals_placeholders` construyen el formulario de intervalos: una sección plegada por tier, con el mínimo y la lista de entidades en la descripción (`flow.py:204-225`). Los comparten el alta y reconfigure por `_show_intervals` (`flow.py:610-636`).
- `check_intervals(profile, tiers, user_input)` valida primero cada intervalo contra `min_tier_interval(profile, tier)` (`interval_too_short` en el campo del tier) y, solo sin errores, el presupuesto: si `request_rate` supera 1 petición por segundo, `interval_budget_exceeded` en `base` (`flow.py:228-239`, `:148`). ADR [0016](../../decisions/0016-instant-tier.md).

Reconfigure, hasta cinco pasos (`flow.py:675-862`):

- `reconfigure`: `host`, número de serie, Device ID y la sección `advanced` con `port` y `unit_id`. Recalcula el `unique_id`; si choca con otra entry, aborta con `already_configured` (`flow.py:681-687`). Valida Device ID y serie como el alta, con el propio Device ID excluido (`flow.py:688-696`), y abre la sonda (`flow.py:698`). Una entry sin Device ID lo deja opcional (`flow.py:755-760`). El serie escrito manda; si está vacío, el leído; si no hay ninguno, la clave desaparece (`flow.py:705-706`).
- `reconfigure_metering`: solo con modos de medición; por defecto, el modo guardado o el primero (`flow.py:707-708`, `:762-772`). Su descripción avisa de qué entidades se mueven o se borran.
- `reconfigure_components`: solo con componentes opcionales; parte de los guardados, o de todos si la entry no tiene la clave. Misma regla de vatímetro forzado que el alta (`flow.py:774-788`).
- `reconfigure_intervals`: mismos campos y comprobaciones que el alta, con los intervalos guardados por defecto (`flow.py:790-833`). Guarda `components`, `intervals`, `metering` (`flow.py:808-810`), `device_id` y `serial_number` y recarga con `async_update_reload_and_abort` (`flow.py:802-822`). No hay update listener.
- `reconfigure_rename`: solo si el Device ID cambia (`flow.py:817-820`). `plan_rename` calcula qué `entity_id` llevan el prefijo generado con el ID viejo; renombra los que no chocan con otra entidad y deja los demás (`flow.py:266-302`, `:835-862`).

`device_unique_id(host, port, unit_id)` devuelve `f"{host.lower()}:{port}:{unit_id}"` (`flow.py:65-66`).

## `TierCoordinator` (`coordinator.py:21-66`)

`DataUpdateCoordinator[TierResult]`, uno por tier de cada equipo.

- `update_interval = interval_s` (`coordinator.py:40`).
- `always_update: bool = False` se pasa tal cual a `DataUpdateCoordinator` (`coordinator.py:33`, `:41-43`). Con `False` HA solo escribe estado si cambia el `TierResult`. `build_runtime` pone `True` en los tiers con fuentes de energía, para que la integral avance con potencia constante (`runtime.py:83-84`, `:95`).
- `keys` es el conjunto de claves habilitadas (`coordinator.py:46`).
- `_async_update_data` llama a `read_tier` (`coordinator.py:55`). `DeviceUnavailable` y `DeviceProtocolError` se convierten en `UpdateFailed`, y las entidades del tier pasan a `unavailable` (`coordinator.py:54-60`).
- Guarda `last_error` y `last_error_at` para diagnostics (`coordinator.py:57-58`).
- Los `DecodeError` de `TierResult.decode_errors` se registran con `warning` una vez por clave hasta que se recupera (`coordinator.py:61-65`).
- El log de disponibilidad (`error` al perder el equipo, `info` al recuperarlo) lo hace `DataUpdateCoordinator` (`coordinator.py:59`).

## `DeviceRuntime` (`runtime.py:19-31`)

Estado en memoria del equipo mientras su entry está cargada: `entry_id`, `title`, `profile`, `selection`, `intervals`, `gateway`, `writer`, `coordinators: dict[PollTier, TierCoordinator]`, `control_states: dict[str, GatedState]`, `device_id` y `serial_number`.

- `selection` es lo elegido en el alta y manda sobre `profile.entities` (`runtime.py:24`). La calcula la raíz con `select(profile, requested, metering)`; `metering` ausente es el primer modo del perfil (`custom_components/modbus_solar/__init__.py:73-76`). Ver [application](../application.md).
- `build_runtime` mezcla `DEFAULT_INTERVALS` con los de `entry.data` y crea un coordinator por tier que tenga entidades de la selección (`runtime.py:70-99`). `DEFAULT_INTERVALS` completa los tiers ausentes en entries anteriores (`runtime.py:81-82`). Calcula `energy_tiers`, los tiers de las fuentes de energía, y les da `always_update=True` (`runtime.py:83-84`, `:95`). Sin selección usa todos los componentes opcionales (`runtime.py:79-80`). Recibe `gateway` y `writer` por separado, aunque la raíz pasa el mismo objeto (`runtime.py:74-75`).
- `control_states` tiene un `GatedState` por control de la selección, con `limit = control.default`. Lo comparten el number y el switch del mismo control (`runtime.py:109-110`).
- `device_id` y `serial_number` salen de `entry.data` (`runtime.py:111-112`); `None` si la entry no los tiene.
- `ModbusSolarConfigEntry = ConfigEntry[DeviceRuntime]` es el tipo de `entry.runtime_data` (`runtime.py:34`).
- `enabled_keys` lee el entity registry con `_is_enabled`: una entidad aún no registrada manda `enabled_default` del perfil; una registrada cuenta si no está deshabilitada (`runtime.py:42-48`, `:51-67`). Cada energía habilitada añade sus `sources`, aunque su sensor de potencia esté deshabilitado (`runtime.py:58-61`). Cada potencia derivada habilitada añade su `source` (`runtime.py:62-66`).

La raíz, antes de crear el runtime, borra del registro las entidades y los dispositivos que ya no se usan (`_remove_unselected`, `custom_components/modbus_solar/__init__.py:28-64`, llamada en `:78`):

- entidades: cuenta como propias las del perfil y las claves de flujo de todos los modos, y borra las que no están en la selección, potencias incluidas (`custom_components/modbus_solar/__init__.py:36-56`);
- dispositivos: borra los de componentes opcionales y de modos (Generador) que no están en `chosen_components` (`custom_components/modbus_solar/__init__.py:57-64`).

Entre «Consumos en Grid» y «Consumos en Cargas Críticas» las claves de red son las mismas: la entidad conserva `unique_id` e historial y cambia de dispositivo. ADR [0015](../../decisions/0015-device-per-component.md).

## Entidades (`entities/`)

- `device_info(entry_id, profile, component, serial)` (`entities/base.py:17-36`) da el dispositivo de un componente. El principal usa el identificador `(DOMAIN, entry_id)` y lleva el número de serie; el resto usa `(DOMAIN, f"{entry_id}_{componente}")` y cuelga del principal con `via_device` (`entities/base.py:26`, `:31-35`). El nombre sale de `translation_key` = `{clave}` y no lleva el Device ID (`entities/base.py:27`).
- `ModbusSolarEntity(CoordinatorEntity[TierCoordinator])` (`entities/base.py:39-78`): acepta `EntitySpec | EnergySpec | GatedLimitSpec | DerivedPowerSpec` y una `key` opcional (`entities/base.py:42-52`): un control da dos entidades, number y switch, y la clave la elige quien construye. `has_entity_name`, `translation_key = key`, `unique_id`, habilitada por defecto según el perfil y el `DeviceInfo` del componente de la entidad (`entities/base.py:53-60`). `entity_category` solo se aplica a un `EntitySpec`: las potencias y energías calculadas son de primer nivel (`entities/base.py:56-58`). `suggested_object_id` pone el Device ID delante del nombre de la entidad; HA antepone el nombre del dispositivo y el `entity_id` queda `sensor.bateria_0_tension`. Solo cuenta en el alta en el registro, y casa con el prefijo de `device_label` del renombrado (`entities/base.py:62-73`, `flow.py:257-263`). Nace `unavailable` hasta la primera lectura correcta (`entities/base.py:75-78`).
- `ModbusSolarSensor` convierte las cadenas de `EntitySpec` a los enums de HA (`entities/factory.py:20-30`). `native_value` sale de `coordinator.data.values` (`entities/factory.py:32-36`).
- `ModbusSolarBinarySensor` (`entities/binary_sensor.py:11-23`): `is_on` es el `bool` ya decodificado del bit; `None` sin datos o sin valor (`entities/binary_sensor.py:18-23`). Los 14 bits del STORAGE son diagnóstico y vienen habilitados.
- `ModbusSolarEnergySensor(ModbusSolarEntity, RestoreSensor)` (`entities/energy.py:14`): kWh, `device_class` `energy`, `state_class` `total_increasing`, precisión 3 (`entities/energy.py:15-18`).
  - `max_gap_s = 3 ×` intervalo del tier: un hueco mayor no se integra (`entities/energy.py:23-25`).
  - Restaura el último total con `async_get_last_sensor_data`; lo que pasa con HA apagado no se integra (`entities/energy.py:27-33`).
  - Muestrea en `_handle_coordinator_update` con `dt_util.utcnow()` (`entities/energy.py:35-41`).
  - Una lectura fallida o una fuente sin valor numérico dan `None` y cortan la serie (`entities/energy.py:43-51`).
  - `native_value` es `total_kwh` del `EnergyAccumulator` (`entities/energy.py:53-55`).
- `ModbusSolarDerivedPowerSensor(ModbusSolarEntity, SensorEntity)` (`entities/derived.py:13`): W, `device_class` `power`, `state_class` `measurement` (`entities/derived.py:14-16`). `native_value` es `filter_power` del valor de la fuente; `None` sin datos o si la fuente no tiene valor numérico (`entities/derived.py:22-31`).
- `build_sensors` devuelve `list[SensorEntity]`: un sensor por `EntitySpec` de la selección con `platform is SENSOR`, un `ModbusSolarEnergySensor` por energía de la selección, suscrito al coordinator del tier de su primera fuente, y un `ModbusSolarDerivedPowerSensor` por potencia de la selección, suscrito al tier de su fuente (`entities/factory.py:39-54`, `:50-53`). `build_binary_sensors` hace lo mismo con `platform is BINARY_SENSOR` (`entities/factory.py:57-62`).
- `ModbusSolarControl(ModbusSolarEntity)` (`entities/control.py:27-33`) es la base del number y del switch de un control. Guarda el `GatedLimitSpec` (`:30`), el `writer` del runtime (`:31`) y el `GatedState` compartido, `runtime.control_states[spec.key]` (`:33`).
  - `write_errors()` (`entities/control.py:16-24`) traduce `DeviceUnavailable`, `DeviceProtocolError` y `EncodeError` a `HomeAssistantError` con `translation_key = write_failed` y el error como placeholder.
- `ModbusSolarNumber(ModbusSolarControl, RestoreNumber)` (`entities/number.py:12`): modo `BOX` (`:13`); mínimo, máximo, paso, unidad y clase salen del `GatedLimitSpec` (`:17-22`).
  - Al añadirse restaura el último valor si está dentro del rango del control y no escribe nada al equipo (`entities/number.py:24-30`).
  - `native_value` es `state.limit` (`entities/number.py:32-34`). `async_set_native_value` llama a `set_limit` dentro de `write_errors` y después escribe el estado (`entities/number.py:36-39`).
- `ModbusSolarSwitch(ModbusSolarControl, SwitchEntity, RestoreEntity)` (`entities/switch.py:16`): usa `spec.switch_key` (`:21`) y `assumed_state = True` porque el equipo no permite leer el ajuste (`:17-18`).
  - Al añadirse restaura `on` u `off` sin escribir al equipo (`entities/switch.py:23-28`). `is_on` es `state.enabled` (`:30-32`).
  - `turn_on` y `turn_off` llaman a `set_enabled` dentro de `write_errors` y después escriben el estado (`entities/switch.py:34-43`).
- `build_numbers` y `build_switches` crean un number y un switch por control de la selección (`entities/factory.py:71-78`). Los dos cuelgan del coordinator del tier de `probe_key` (`entities/factory.py:65-68`): hasta la primera lectura correcta de ese tier, o con el equipo caído, quedan `unavailable`. Ver [features/control](../../features/control.md) y ADR [0012](../../decisions/0012-optimistic-restored-state.md).
- `sensor.py:10-13`, `binary_sensor.py:10-13`, `number.py:10-13` y `switch.py:10-13` añaden las entidades de la entry con `build_sensors`, `build_binary_sensors`, `build_numbers` y `build_switches` sobre `entry.runtime_data`. La lista `PLATFORMS` está en `custom_components/modbus_solar/__init__.py:25`.

## Identificadores

| Qué | Formato | Cita |
|---|---|---|
| `unique_id` de la entry | `host.lower():puerto:unidad` | `flow.py:65-66` |
| Dispositivo principal | `(DOMAIN, entry_id)` | `entities/base.py:26` |
| Dispositivo de un componente | `(DOMAIN, f"{entry_id}_{componente}")`, con `via_device` al principal | `entities/base.py:26`, `:35` |
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
