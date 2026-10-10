# Arquitectura: adaptadores de entrada

Documento vivo. Todo lo que habla con Home Assistant. Rutas bajo `custom_components/modbus_solar/adapters/inbound/` salvo indicación. No importa `adapters.outbound` (`pyproject.toml:58-61`) ni `modbus_connection`: solo ve errores de dominio.

## Flow (`flow.py`)

La raíz inyecta `catalog` y `gateway_factory` (`custom_components/modbus_solar/config_flow.py:36-38`).

### `DeviceConfigFlow` (`flow.py:392-1042`)

Una config entry por equipo (ADR [0010](../../decisions/0010-entry-per-device.md)). `VERSION = 2` (`flow.py:395`). Detalle de pantallas y textos en [features/device-setup](../../features/device-setup.md).

Estado del flow entre pasos: `_components`, `_metering`, `_costs` (lo elegido; `None` = sin seguimiento) y `_cost_modes` (el modo, `fixed` o `dynamic`, de cada sentido entre `costs` y `cost_prices`) (`flow.py:403-410`).

Alta, en este orden:

- Paso `user`: `SelectSelector` en modo lista con una opción por marca (`flow.py:418-424`).
- Paso `model`: un perfil por opción; la opción es el id sin puntos, válido como `translation_key` (`flow.py:108-110`, `:426-450`). Al entrar olvida la sonda, los componentes, el modo de medición y los costes (`flow.py:433-436`).
- Paso `connection`: `host` y una sección plegada `advanced` con `port` y `unit_id`, por defecto `profile.default_port` y `profile.default_unit_id` (`flow.py:492-551`).
  - El duplicado se detecta antes de abrir conexión y aborta con `already_configured` (`flow.py:501-502`).
  - Valida con `_try_probe` (`flow.py:479-490`, `:503`): abre `gateway_factory` y llama a `probe_device`, todo dentro de `asyncio.timeout(PROBE_TIMEOUT_S)`, 20 s (`flow.py:67`, `:1039-1042`).
  - Con error, vuelve el formulario con lo escrito y un selector de modelo para corregirlo; los puertos del modelo nuevo solo se aplican si no se tocaron. Cambiar de modelo olvida componentes, modo de medición y costes (`_switch_profile`, `flow.py:452-469`, `:463-466`, `:520-522`).
  - Con modos de medición sigue a `metering`; si no, con componentes opcionales a `components`, y sin ellos a `readings` (`flow.py:509-514`).
- Paso `metering`: desplegable `SelectSelector` con los modos del perfil y `translation_key = metering_mode`; por defecto, lo ya elegido o el primer modo (`flow.py:553-561`, `_show_metering` en `:610-623`). Si el modo tiene algún flujo con coste (`has_costs`, `flow.py:260-263`), sigue a `costs`; si no, descarta los costes elegidos (`flow.py:557-559`) y sigue como `_after_metering`: a `components` o a `readings` (`flow.py:560`, `:563-567`). ADR [0017](../../decisions/0017-metering-mode.md).
- Paso `costs`: casilla `enabled` y, por sentido, un desplegable `import_mode` / `export_mode` con `fixed` o `dynamic` (`flow.py:569-576`, `costs_schema` en `:266-277`, `_show_costs` en `:587-593`). Sin marcar la casilla, descarta los costes y sigue como `_after_metering` (`flow.py:571-573`). Marcada, guarda los modos en `_cost_modes` y sigue a `cost_prices` (`flow.py:574-575`). Por defecto, lo ya elegido; sin nada, casilla desmarcada y modo `fixed` (`flow.py:267`, `:273-276`).
- Paso `cost_prices`: un campo por sentido según su modo (`flow.py:578-585`, `cost_prices_schema` en `:280-288`, `_show_cost_prices` en `:595-608`). `fixed`: `{sentido}_price`, un `NumberSelector` en modo caja de 0 a 10 €/kWh con `step="any"` (`flow.py:73-75`, `:284-285`). `dynamic`: `{sentido}_entity`, un `EntitySelector` del dominio `sensor` (`flow.py:286-287`). Valida con `price_errors` (`flow.py:581`) y, sin errores, guarda `costs_data(...)` en `_costs` y sigue como `_after_metering` (`flow.py:582-584`). Los valores sugeridos son los guardados de los sentidos que conservan su modo (`cost_prices_suggested`, `flow.py:291-302`); tras un error se conserva lo escrito (`flow.py:603`).
- Paso `components`: selector múltiple con los componentes opcionales del perfil; por defecto, los marcados `default`, o lo ya elegido al volver atrás (`flow.py:625-679`). `_show_components` marca además el vatímetro del modo, `required_component` (`flow.py:652-657`). Si el usuario lo desmarca, `missing_meter` da el error `metering_component_required` con los placeholders `component` y `mode` (`flow.py:329-332`, `:629-632`, `:668-673`).
- Paso `readings`: menú con las lecturas de la sonda de los componentes elegidos y tres salidas, `name`, `model` y `connection` (`flow.py:681-693`).
- Paso `name`: nombre, Device ID y número de serie (`flow.py:695-748`).
  - El Device ID propuesto es el menor entero libre entre las entries del mismo `device_type` (`flow.py:87-105`, `:701`). Uno repetido da `device_id_in_use` (`flow.py:706-707`).
  - Un número de serie escrito solo admite letras y números ASCII; si no, `invalid_serial_number` (`flow.py:82-84`, `:708-709`).
  - Manda el serie escrito; si está vacío, el leído por la sonda; si no hay ninguno, no se guarda (`flow.py:711-714`).
- Paso `intervals`: un campo por tier con entidades (`flow.py:779-817`). Crea la entry con `title = name` y `data = {host, port, unit_id, profile, components, intervals, metering, costs, device_id, serial_number}`; `metering` solo si el perfil tiene modos, `costs` solo si hay seguimiento, y `device_id` y `serial_number` solo si existen (`flow.py:790-806`, `:797-801`). Los tiers sin entidades conservan `DEFAULT_INTERVALS` (`flow.py:794-795`).

Errores del formulario de conexión (`flow.py:479-490`):

| Error de dominio | Clave del formulario | Cita |
|---|---|---|
| `EndpointInUse` | `endpoint_in_use` | `flow.py:485-486` |
| `DeviceUnavailable`, `TimeoutError` | `cannot_connect` | `flow.py:487-488` |
| `DeviceProtocolError`, `DecodeError` | `invalid_response` | `flow.py:489-490` |

Funciones auxiliares:

- `format_readings(profile, selection, result, translations, language)` (`flow.py:121-156`) escribe las lecturas de la sonda agrupadas por componente: un título por dispositivo y una línea `- {nombre}: {valor} {unidad}` por sensor de la selección que la sonda leyó. Los `binary_sensor` no salen (`flow.py:136-137`). Nombre y estado del enum salen de `component.modbus_solar.entity.sensor.<key>`; sin traducción, la clave. `None` se muestra como `—`. Los números llevan separador de miles según el idioma (`format_number`, `flow.py:113-118`).
- `present_tiers(selection)` da los tiers con entidades de los componentes elegidos, en el orden de `PollTier` (`flow.py:164-166`).
- `entity_list(profile, selection, tier, translations)` lista las entidades de un tier con su dispositivo: leídas, potencias, energías y costes calculados, y controles; las desactivadas por defecto llevan una marca. Los costes entran con el tier de su fuente, junto a las potencias y las energías (`flow.py:197`, `:203-207`). Los dispositivos de los modos (Generador) van detrás de los opcionales (`flow.py:169-219`, `:175-180`).
- `intervals_schema` y `intervals_placeholders` construyen el formulario de intervalos: una sección plegada por tier, con el mínimo y la lista de entidades en la descripción (`flow.py:222-243`). Los comparten el alta y reconfigure por `_show_intervals` (`flow.py:750-777`), que recibe también los costes para calcular la selección (`flow.py:756`, `:763`).
- `check_intervals(profile, tiers, user_input)` valida primero cada intervalo contra `min_tier_interval(profile, tier)` (`interval_too_short` en el campo del tier) y, solo sin errores, el presupuesto: si `request_rate` supera 1 petición por segundo, `interval_budget_exceeded` en `base` (`flow.py:246-257`, `:161`). ADR [0016](../../decisions/0016-instant-tier.md).
- Seguimiento de costes (`flow.py:68-75`, `:260-326`): las constantes `CONF_ENABLED`, `COST_DIRECTIONS = ("import", "export")`, `MODE_FIXED`, `MODE_DYNAMIC` y `PRICE`, y las funciones `has_costs`, `costs_schema`, `cost_prices_schema`, `cost_prices_suggested`, `price_errors` y `costs_data`. Las comparten el alta y reconfigure.
  - `has_costs(profile, metering)` es cierto si el modo tiene algún flujo con `cost_key`: «Aislada» no (`flow.py:260-263`).
  - `price_errors(hass, modes, user_input)`: cada entidad dinámica debe existir y tener una `unit_of_measurement` de `PRICE_UNITS`; si no, `price_unit_invalid` en su campo. No mira el estado: puede estar caído (`flow.py:305-315`).
  - `costs_data(modes, user_input)` da lo que se guarda en `entry.data["costs"]`: por sentido, `{"mode": "fixed", "price": float}` o `{"mode": "dynamic", "entity_id": str}` (`flow.py:318-326`).
  - `COST_DIRECTIONS` también existe en `application/selection.py` como dict de signo a sentido (`custom_components/modbus_solar/application/selection.py:14`): dos constantes con el mismo nombre y los mismos sentidos que hay que mantener a la par.

Reconfigure, hasta siete pasos (`flow.py:819-1037`):

- `reconfigure`: `host`, número de serie, Device ID y la sección `advanced` con `port` y `unit_id`. Recalcula el `unique_id`; si choca con otra entry, aborta con `already_configured` (`flow.py:825-831`). Valida Device ID y serie como el alta, con el propio Device ID excluido (`flow.py:832-840`), y abre la sonda (`flow.py:842`). Una entry sin Device ID lo deja opcional (`flow.py:899-904`). El serie escrito manda; si está vacío, el leído; si no hay ninguno, la clave desaparece (`flow.py:849-850`).
- `reconfigure_metering`: solo con modos de medición; por defecto, el modo guardado o el primero (`flow.py:851-852`, `:906-916`). Su descripción avisa de qué entidades se mueven o se borran. Como el alta, sigue a `reconfigure_costs` si el modo tiene flujos con coste; si no, descarta los costes y sigue como `_after_reconfigure_metering` (`flow.py:911-914`, `:918-922`).
- `reconfigure_costs` y `reconfigure_cost_prices`: los mismos formularios que `costs` y `cost_prices` del alta (`_show_costs` y `_show_cost_prices`), con `entry.data["costs"]` como valores guardados (`flow.py:924-942`). Con la casilla desmarcada, descarta los costes (`flow.py:927-929`).
- `reconfigure_components`: solo con componentes opcionales; parte de los guardados, o de todos si la entry no tiene la clave. Misma regla de vatímetro forzado que el alta (`flow.py:944-958`).
- `reconfigure_intervals`: mismos campos y comprobaciones que el alta, con los intervalos guardados por defecto (`flow.py:960-1008`). Guarda `components`, `intervals`, `metering` (`flow.py:978-980`), `device_id`, `serial_number` y `costs`; si `device_id`, `serial_number` o `costs` valen `None`, quita su clave de `entry.data` (`flow.py:981-989`). Recarga con `async_update_reload_and_abort` (`flow.py:972-996`). No hay update listener.
- `reconfigure_rename`: solo si el Device ID cambia (`flow.py:991-994`). `plan_rename` calcula qué `entity_id` llevan el prefijo generado con el ID viejo; renombra los que no chocan con otra entidad y deja los demás (`flow.py:353-389`, `:1010-1037`).

`device_unique_id(host, port, unit_id)` devuelve `f"{host.lower()}:{port}:{unit_id}"` (`flow.py:78-79`).

## `TierCoordinator` (`coordinator.py:21-66`)

`DataUpdateCoordinator[TierResult]`, uno por tier de cada equipo.

- `update_interval = interval_s` (`coordinator.py:40`).
- `always_update: bool = False` se pasa tal cual a `DataUpdateCoordinator` (`coordinator.py:33`, `:41-43`). Con `False` HA solo escribe estado si cambia el `TierResult`. `build_runtime` pone `True` en los tiers con fuentes de energía o de coste, para que la integral avance con potencia constante (`runtime.py:90-93`, `:104`).
- `keys` es el conjunto de claves habilitadas (`coordinator.py:46`).
- `_async_update_data` llama a `read_tier` (`coordinator.py:55`). `DeviceUnavailable` y `DeviceProtocolError` se convierten en `UpdateFailed`, y las entidades del tier pasan a `unavailable` (`coordinator.py:54-60`).
- Guarda `last_error` y `last_error_at` para diagnostics (`coordinator.py:57-58`).
- Los `DecodeError` de `TierResult.decode_errors` se registran con `warning` una vez por clave hasta que se recupera (`coordinator.py:61-65`).
- El log de disponibilidad (`error` al perder el equipo, `info` al recuperarlo) lo hace `DataUpdateCoordinator` (`coordinator.py:59`).

## `DeviceRuntime` (`runtime.py:20-33`)

Estado en memoria del equipo mientras su entry está cargada: `entry_id`, `title`, `profile`, `selection`, `intervals`, `gateway`, `writer`, `coordinators: dict[PollTier, TierCoordinator]`, `control_states: dict[str, GatedState]`, `device_id`, `serial_number` y `costs`.

- `selection` es lo elegido en el alta y manda sobre `profile.entities` (`runtime.py:25`). La calcula la raíz con `select(profile, requested, metering, data.get(CONF_COSTS))`; `metering` ausente es el primer modo del perfil (`custom_components/modbus_solar/__init__.py:75-78`). Ver [application](../application.md).
- `build_runtime` mezcla `DEFAULT_INTERVALS` con los de `entry.data` y crea un coordinator por tier que tenga entidades de la selección (`runtime.py:77-108`). `DEFAULT_INTERVALS` completa los tiers ausentes en entries anteriores (`runtime.py:88-89`). Calcula `energy_tiers`, los tiers de las fuentes de energía y de las fuentes de coste, y les da `always_update=True` (`runtime.py:90-93`, `:104`). Sin selección usa todos los componentes opcionales (`runtime.py:86-87`). Recibe `gateway` y `writer` por separado, aunque la raíz pasa el mismo objeto (`runtime.py:81-82`).
- `control_states` tiene un `GatedState` por control de la selección, con `limit = control.default`. Lo comparten el number y el switch del mismo control (`runtime.py:118-119`).
- `device_id` y `serial_number` salen de `entry.data` (`runtime.py:120-121`); `None` si la entry no los tiene.
- `costs` es `entry.data["costs"]`: el precio de cada sentido, `{"mode": "fixed", "price"}` o `{"mode": "dynamic", "entity_id"}`; `None` sin seguimiento (`runtime.py:33`, `:122`). Lo leen los sensores de coste por `build_sensors` (`entities/factory.py:55-59`).
- `ModbusSolarConfigEntry = ConfigEntry[DeviceRuntime]` es el tipo de `entry.runtime_data` (`runtime.py:36`).
- `enabled_keys` lee el entity registry con `_is_enabled`: una entidad aún no registrada manda `enabled_default` del perfil; una registrada cuenta si no está deshabilitada (`runtime.py:44-50`, `:53-74`). Cada energía habilitada añade sus `sources`, aunque su sensor de potencia esté deshabilitado (`runtime.py:60-63`). Cada potencia derivada habilitada añade su `source` (`runtime.py:64-68`). Cada coste habilitado añade también su `source`, aunque su potencia y su energía estén deshabilitadas (`runtime.py:69-73`).

La raíz, antes de crear el runtime, borra del registro las entidades y los dispositivos que ya no se usan (`_remove_unselected`, `custom_components/modbus_solar/__init__.py:28-66`, llamada en `:80`):

- entidades: cuenta como propias las del perfil y las claves de flujo de todos los modos, incluidas las `cost_key` (`custom_components/modbus_solar/__init__.py:38-39`), y borra las que no están en la selección, potencias y costes incluidos (`custom_components/modbus_solar/__init__.py:46-58`). Si la entry ya no tiene `costs`, `selection.costs` queda vacía y los sensores de coste se borran del registro (`custom_components/modbus_solar/__init__.py:51`, `:55-58`);
- dispositivos: borra los de componentes opcionales y de modos (Generador) que no están en `chosen_components` (`custom_components/modbus_solar/__init__.py:59-66`).

Entre «Consumos en Grid» y «Consumos en Cargas Críticas» las claves de red son las mismas, también las de coste: la entidad conserva `unique_id` e historial y cambia de dispositivo (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:172-192`, `:453-455`). ADR [0015](../../decisions/0015-device-per-component.md).

## Entidades (`entities/`)

- `device_info(entry_id, profile, component, serial)` (`entities/base.py:17-36`) da el dispositivo de un componente. El principal usa el identificador `(DOMAIN, entry_id)` y lleva el número de serie; el resto usa `(DOMAIN, f"{entry_id}_{componente}")` y cuelga del principal con `via_device` (`entities/base.py:26`, `:31-35`). El nombre sale de `translation_key` = `{clave}` y no lleva el Device ID (`entities/base.py:27`).
- `ModbusSolarEntity(CoordinatorEntity[TierCoordinator])` (`entities/base.py:39-78`): acepta `EntitySpec | EnergySpec | GatedLimitSpec | DerivedPowerSpec | DerivedCostSpec` y una `key` opcional (`entities/base.py:42-52`): un control da dos entidades, number y switch, y la clave la elige quien construye. `has_entity_name`, `translation_key = key`, `unique_id`, habilitada por defecto según el perfil y el `DeviceInfo` del componente de la entidad (`entities/base.py:53-60`). `entity_category` solo se aplica a un `EntitySpec`: las potencias, energías y costes calculados son de primer nivel (`entities/base.py:56-58`). `suggested_object_id` pone el Device ID delante del nombre de la entidad; HA antepone el nombre del dispositivo y el `entity_id` queda `sensor.bateria_0_tension`. Solo cuenta en el alta en el registro, y casa con el prefijo de `device_label` del renombrado (`entities/base.py:62-73`, `flow.py:344-350`). Nace `unavailable` hasta la primera lectura correcta (`entities/base.py:75-78`).
- `ModbusSolarSensor` convierte las cadenas de `EntitySpec` a los enums de HA (`entities/factory.py:21-31`). `native_value` sale de `coordinator.data.values` (`entities/factory.py:33-37`).
- `ModbusSolarBinarySensor` (`entities/binary_sensor.py:11-23`): `is_on` es el `bool` ya decodificado del bit; `None` sin datos o sin valor (`entities/binary_sensor.py:18-23`). Los 14 bits del STORAGE son diagnóstico y vienen habilitados.
- `ModbusSolarEnergySensor(ModbusSolarEntity, RestoreSensor)` (`entities/energy.py:14`): kWh, `device_class` `energy`, `state_class` `total_increasing`, precisión 3 (`entities/energy.py:15-18`).
  - `max_gap_s = 3 ×` intervalo del tier: un hueco mayor no se integra (`entities/energy.py:23-25`).
  - Restaura el último total con `async_get_last_sensor_data`; lo que pasa con HA apagado no se integra (`entities/energy.py:27-33`).
  - Muestrea en `_handle_coordinator_update` con `dt_util.utcnow()` (`entities/energy.py:35-41`).
  - Una lectura fallida o una fuente sin valor numérico dan `None` y cortan la serie (`entities/energy.py:43-51`).
  - `native_value` es `total_kwh` del `EnergyAccumulator` (`entities/energy.py:53-55`).
- `ModbusSolarDerivedPowerSensor(ModbusSolarEntity, SensorEntity)` (`entities/derived.py:13`): W, `device_class` `power`, `state_class` `measurement` (`entities/derived.py:14-16`). `native_value` es `filter_power` del valor de la fuente; `None` sin datos o si la fuente no tiene valor numérico (`entities/derived.py:22-31`).
- `ModbusSolarCostSensor(ModbusSolarEntity, RestoreSensor)` (`entities/cost.py:21-81`): euros acumulados de un flujo de red, la energía de su fuente por el precio. `device_class` `monetary`, `state_class` `total` (HA no admite `total_increasing` con `monetary`, y un precio negativo resta), unidad `EUR`, precisión 2 (`entities/cost.py:22-26`).
  - Recibe el precio de su sentido, `runtime.costs[direction]` (`entities/cost.py:28-33`).
  - `max_gap_s = 3 ×` intervalo del tier, como la energía: un hueco mayor no se cobra (`entities/cost.py:34-36`).
  - Restaura el último total con `async_get_last_sensor_data` si es numérico; lo que pasa con HA apagado no se integra (`entities/cost.py:39-44`). La energía pendiente de precio no se guarda: tras un reinicio se pierde.
  - Muestrea en `_handle_coordinator_update` con `dt_util.utcnow()` (`entities/cost.py:46-49`, `:51-61`).
  - Precio `fixed`: el `float` guardado. Precio `dynamic`: lee el estado de la entidad con `hass.states.get` y lo convierte a €/kWh con `price_per_kwh` y su `unit_of_measurement`; sin entidad, sin estado numérico o con otra unidad da `None` y la energía queda pendiente (`entities/cost.py:63-69`). Avisa con `warning` una vez al caer el precio y con `info` al volver (`entities/cost.py:54-60`).
  - Una lectura fallida o una fuente sin valor numérico dan `None` y cortan la serie (`entities/cost.py:71-77`).
  - `native_value` es `total_eur` del `CostAccumulator` (`entities/cost.py:79-81`). Ver [domain](../domain.md).
- `build_sensors` devuelve `list[SensorEntity]`: un sensor por `EntitySpec` de la selección con `platform is SENSOR`, un `ModbusSolarEnergySensor` por energía de la selección, suscrito al coordinator del tier de su primera fuente, un `ModbusSolarDerivedPowerSensor` por potencia de la selección, suscrito al tier de su fuente, y un `ModbusSolarCostSensor` por coste de la selección, suscrito al tier de su fuente y con el precio de su sentido, `runtime.costs[cost.direction]` (`entities/factory.py:40-60`, `:51-54`, `:55-59`). `build_binary_sensors` hace lo mismo con `platform is BINARY_SENSOR` (`entities/factory.py:63-68`).
- `ModbusSolarControl(ModbusSolarEntity)` (`entities/control.py:27-33`) es la base del number y del switch de un control. Guarda el `GatedLimitSpec` (`:30`), el `writer` del runtime (`:31`) y el `GatedState` compartido, `runtime.control_states[spec.key]` (`:33`).
  - `write_errors()` (`entities/control.py:16-24`) traduce `DeviceUnavailable`, `DeviceProtocolError` y `EncodeError` a `HomeAssistantError` con `translation_key = write_failed` y el error como placeholder.
- `ModbusSolarNumber(ModbusSolarControl, RestoreNumber)` (`entities/number.py:12`): modo `BOX` (`:13`); mínimo, máximo, paso, unidad y clase salen del `GatedLimitSpec` (`:17-22`).
  - Al añadirse restaura el último valor si está dentro del rango del control y no escribe nada al equipo (`entities/number.py:24-30`).
  - `native_value` es `state.limit` (`entities/number.py:32-34`). `async_set_native_value` llama a `set_limit` dentro de `write_errors` y después escribe el estado (`entities/number.py:36-39`).
- `ModbusSolarSwitch(ModbusSolarControl, SwitchEntity, RestoreEntity)` (`entities/switch.py:16`): usa `spec.switch_key` (`:21`) y `assumed_state = True` porque el equipo no permite leer el ajuste (`:17-18`).
  - Al añadirse restaura `on` u `off` sin escribir al equipo (`entities/switch.py:23-28`). `is_on` es `state.enabled` (`:30-32`).
  - `turn_on` y `turn_off` llaman a `set_enabled` dentro de `write_errors` y después escriben el estado (`entities/switch.py:34-43`).
- `build_numbers` y `build_switches` crean un number y un switch por control de la selección (`entities/factory.py:77-84`). Los dos cuelgan del coordinator del tier de `probe_key` (`entities/factory.py:71-74`): hasta la primera lectura correcta de ese tier, o con el equipo caído, quedan `unavailable`. Ver [features/control](../../features/control.md) y ADR [0012](../../decisions/0012-optimistic-restored-state.md).
- `sensor.py:10-13`, `binary_sensor.py:10-13`, `number.py:10-13` y `switch.py:10-13` añaden las entidades de la entry con `build_sensors`, `build_binary_sensors`, `build_numbers` y `build_switches` sobre `entry.runtime_data`. La lista `PLATFORMS` está en `custom_components/modbus_solar/__init__.py:25`.

## Identificadores

| Qué | Formato | Cita |
|---|---|---|
| `unique_id` de la entry | `host.lower():puerto:unidad` | `flow.py:78-79` |
| Dispositivo principal | `(DOMAIN, entry_id)` | `entities/base.py:26` |
| Dispositivo de un componente | `(DOMAIN, f"{entry_id}_{componente}")`, con `via_device` al principal | `entities/base.py:26`, `:35` |
| `unique_id` de entidad | `f"{entry_id}_{key}"` | `runtime.py:39-41` |

Un dispositivo por componente elegido (ADR [0015](../../decisions/0015-device-per-component.md)). El `entry_id` es un ULID: cambiar el host en reconfigure no duplica entidades ni dispositivos (`runtime.py:40`). El Device ID va en el `entity_id` de las entidades nuevas, no en el nombre del dispositivo; no entra en ningún identificador.

## Diagnostics (`diagnostics.py`, `custom_components/modbus_solar/diagnostics.py`)

`device_diagnostics(runtime, entry_data)` devuelve (`diagnostics.py:15-44`):

- `profile` (id) e `intervals` (`diagnostics.py:40-41`);
- por tier: `last_update_success`, `last_error` y `last_error_at` (`diagnostics.py:16-23`);
- por entidad de la selección: `address`, `dtype`, `word_order`, `scale`, `raw` y `value` (`diagnostics.py:24-37`). Las energías, potencias y costes calculados no salen: no tienen registro (`diagnostics.py:25`). Usa el último `TierResult` correcto, también tras un fallo (`diagnostics.py:26`);
- `entry` con los datos de la entry y `host` y `serial_number` ocultos mediante `async_redact_data` (`diagnostics.py:12`, `:39`). `costs` sale sin ocultar: los precios fijos y los `entity_id` de las entidades de precio.

La raíz delega: `async_get_config_entry_diagnostics` y `async_get_device_diagnostics` devuelven lo mismo, el diagnostics del equipo de la entry (`custom_components/modbus_solar/diagnostics.py:12-19`).

Uso: verificar en la VM los supuestos de escala y `word_order` de los perfiles.
