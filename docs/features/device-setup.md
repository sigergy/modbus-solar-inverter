# Funcionalidad: alta y configuración de dispositivos

Documento vivo. Rutas bajo `custom_components/modbus_solar/` salvo indicación. Los nombres de campo y de error son las claves de `strings.json`.

## Alta de un dispositivo

Una config entry por equipo físico (ADR [0010](../decisions/0010-entry-per-device.md)). Dentro de la entry, un dispositivo de HA por componente (ADR [0015](../decisions/0015-device-per-component.md)). «Añadir integración» → Modbus Solar abre un flow de hasta ocho pasos (`adapters/inbound/flow.py:305-673`):

`user` (marca) → `model` → `connection` → `metering` → `components` → `readings` (menú) → `name` → `intervals`.

El paso `metering` solo sale si el perfil declara modos de medición de red; hoy, el STORAGE 1Play TL M. El paso `components` solo sale si el perfil declara componentes opcionales (`adapters/inbound/flow.py:416-421`, `:463-467`).

### Paso 1 · marca (`user`)

- Campo `brand`, una lista con una marca por línea, sin valor por defecto. Siempre se muestra, aunque solo haya una marca (`adapters/inbound/flow.py:327-333`).
- Opciones: `catalog.brands()`, con la etiqueta de `BRAND_TITLES` (`application/catalog.py:16-17`, `const.py:17`).

### Paso 2 · modelo (`model`)

- Campo `profile`, una lista con los perfiles de la marca elegida (`adapters/inbound/flow.py:335-358`).
- Para un STORAGE 1Play TL M hay que elegir el perfil `ingeteam.oneplay_storage`.
- Al volver aquí desde las lecturas se olvidan las lecturas, los componentes y la medición de red (`adapters/inbound/flow.py:341-344`).

### Paso 3 · conexión (`connection`)

| Campo | Valor por defecto | Rango |
|---|---|---|
| `host` | — | texto |
| `port`, en la sección plegada `advanced` | `profile.default_port` (502 en Ingeteam) | 1-65535 |
| `unit_id`, en la sección plegada `advanced` | `profile.default_unit_id` (1 en Ingeteam) | 1-247 |

Esquema en `adapters/inbound/flow.py:399-458`; rangos en `:55-56`. Puerto y unidad por defecto de los perfiles Ingeteam: `profiles/ingeteam/oneplay.py:14-15` y `profiles/ingeteam/oneplay_storage.py:201-202`.

Abort `already_configured`: mismo `host:port:unit_id`, con el host en minúsculas (`adapters/inbound/flow.py:65-66`, `:408-409`). Se comprueba antes de abrir conexión.

Tras un error, el formulario añade el campo `profile` («Modelo»): HA no ofrece botones secundarios y así se corrige el modelo sin cerrar el flujo. Cambiar de marca exige cerrarlo. Si el modelo cambia, los puertos y la unidad del modelo nuevo solo se aplican si no se tocaron, y se olvidan los componentes y la medición de red elegidos (`adapters/inbound/flow.py:360-376`, `:426-430`).

#### Sonda

Al enviar, el flow abre una unit temporal (`config_flow.py:20-33`) y llama a `probe_device` (`application/probe.py:19-32`), que devuelve un `ProbeResult` con las lecturas y el número de serie:

1. Lee la entidad `probe_key` del perfil, `inverter_state` en los dos perfiles Ingeteam e `irradiance` en el sensor de irradiancia (`profiles/mencke_tegtmeyer/si_rs485.py:20`): input 30016 en el STORAGE (`profiles/ingeteam/oneplay_storage.py:203`) y holding `0x101D` en el 1Play sin storage (`profiles/ingeteam/oneplay.py:16`). Un valor fuera del enum lanza `DecodeError`.
2. Lee los tiers `fast` e `instant`, limitados a las entidades habilitadas por defecto (`application/probe.py:24-26`).
3. Si el perfil declara `serial`, lo lee como texto ASCII (`application/probe.py:35-43`, `domain/decode.py:39-44`). Su fallo no invalida la sonda: el número de serie queda en `None`.

Todo dentro de un tiempo máximo de `PROBE_TIMEOUT_S = 20` s (`adapters/inbound/flow.py:62`, `:864-867`). Si falla, no se crea la entry y el formulario vuelve con lo que escribió el usuario.

Ningún perfil declara hoy `serial`: los mapas de Ingeteam no documentan el registro. El mecanismo está listo para el perfil que lo declare.

#### Errores del formulario

| Error | Cuándo | Origen |
|---|---|---|
| `cannot_connect` | el equipo no responde o la sonda supera 20 s | `DeviceUnavailable` o `TimeoutError` (`adapters/inbound/flow.py:394-395`) |
| `endpoint_in_use` | el endpoint ya está en uso con otros parámetros de enlace | `HomeAssistantError` de `async_get_temporary_unit`, traducido a `EndpointInUse` (`config_flow.py:30-32`, `adapters/inbound/flow.py:392-393`) |
| `invalid_response` | excepción Modbus o valor fuera del enum | `DeviceProtocolError` o `DecodeError` (`adapters/inbound/flow.py:396-397`, `domain/decode.py:30-31`) |

### Paso 4 · medición de red (`metering`)

Dice qué vatímetro mide el intercambio con la red. No hay registro que lo diga, así que lo elige el usuario (ADR [0017](../decisions/0017-metering-mode.md)).

- Campo `metering` («Medición de red»), un desplegable con los modos del perfil (`adapters/inbound/flow.py:460-483`).
- Valor por defecto: el elegido antes en el mismo flujo; si no, el primer modo del perfil.
- Opciones del STORAGE 1Play TL M, en este orden (`profiles/ingeteam/oneplay_storage.py:448-467`):

| Clave | Opción | Cuándo | Vatímetro (registro) | Entidades | Dispositivo |
|---|---|---|---|---|---|
| `grid_loads` (por defecto) | Consumos en Grid | vatímetro externo en el punto de conexión | externo (30072) | Potencia de red, Potencia a la red, Energía importada, Energía exportada | Red |
| `critical_loads` | Consumos en Cargas Críticas | todos los consumos en la salida de cargas críticas | interno (30052) | las mismas cuatro | Vatímetro interno |
| `off_grid` | Aislada | sin red; las bornas de red pueden llevar un grupo electrógeno | interno (30052) | Potencia del generador, Energía del generador | Generador |

Casos de instalación: `ABH2014IQM01`, apdo. 19.8, pág. 60; entrada «grid/genset» de las bornas de red: apdo. 11, pág. 32. Qué miden esas entidades: [monitoring](monitoring.md#medición-de-red).

### Paso 5 · componentes (`components`)

- Campo `components`, lista de casillas con los componentes opcionales del perfil. El principal va siempre y no sale en la lista (`adapters/inbound/flow.py:485-539`).
- Marcados por defecto los de `ComponentSpec.default` (`domain/profile.py:28-30`). En el STORAGE, vatímetro interno y cargador VE salen desmarcados (`profiles/ingeteam/oneplay_storage.py:205-213`).
- **Componente forzado.** El vatímetro del modo elegido sale marcado, aunque el perfil lo tenga desmarcado: Red con «Consumos en Grid», Vatímetro interno con los otros dos (`adapters/inbound/flow.py:512-517`, `application/selection.py:28-30`). Si se desmarca, error `metering_component_required`: «{component} hace falta para «{mode}». Márcalo o cambia la medición de red.» (`adapters/inbound/flow.py:242-245`, `:489-492`, `:528-533`).
- Generador no sale en la lista: no es un componente opcional del perfil. Lo crea el modo «Aislada».

### Paso 6 · lecturas (`readings`)

Menú con tres opciones: `name` (continuar), `model` y `connection` (volver). Muestra el host y las lecturas de la sonda (`adapters/inbound/flow.py:541-553`).

- `format_readings` escribe las lecturas agrupadas por componente, el principal primero, con el nombre traducido de la entidad. Un enum muestra su estado traducido; un número, su unidad; un valor sin decodificar, `—`. Solo cuenta sensores: los bits del BMS no se cotejan con la pantalla del equipo (`adapters/inbound/flow.py:108-145`).
- Las traducciones salen de `async_get_translations` en el idioma de HA (`adapters/inbound/flow.py:378-384`).

### Paso 7 · nombre (`name`)

| Campo | Valor por defecto | Notas |
|---|---|---|
| `name` | `"{marca} {primer modelo}"`, p. ej. `Ingeteam STORAGE 1Play TL M` | título de la entry |
| `device_id` | el menor entero libre del mismo `device_type` | entero ≥ 0, obligatorio |
| `serial_number` | vacío | opcional; solo letras y números ASCII |

Formulario en `adapters/inbound/flow.py:555-636`.

- **Device ID.** Distingue equipos del mismo tipo: va en el `entity_id` de las entidades nuevas (`sensor.bateria_0_tension`), no en el nombre del dispositivo, que queda «Batería» (`adapters/inbound/entities/base.py:17-36`, `:62-73`). Debe ser único por `device_type` entre las entries; si no, error `device_id_in_use` (`adapters/inbound/flow.py:74-92`, `:566-567`).
- **Número de serie.** Lo escrito manda; si está vacío, el leído por la sonda; si no hay ninguno, no se guarda. Un valor con espacios o símbolos da `invalid_serial_number` (`adapters/inbound/flow.py:69-71`, `:568-575`). La ayuda del campo cambia según el perfil y la sonda: `none`, `read` o `unreadable` (`adapters/inbound/flow.py:581-588`).
- El número de serie se muestra en el dispositivo principal (`adapters/inbound/entities/base.py:32-33`).

### Paso 8 · intervalos (`intervals`)

- Una sección plegada por tier que tenga entidades en los componentes elegidos, en el orden de `PollTier` (`adapters/inbound/flow.py:151-153`, `:204-214`). La descripción de cada campo lista sus entidades por dispositivo, con las desactivadas marcadas, las potencias y energías calculadas y los controles (`adapters/inbound/flow.py:156-201`).
- Cada intervalo debe ser ≥ `min_tier_interval(profile, tier)`; si no, error `interval_too_short` en el campo del tier (`adapters/inbound/flow.py:233-235`).
- Los intervalos, juntos, no pueden pedir más de una petición por segundo (`request_rate`, `application/poller.py:52-54`). Si se pasa, error `interval_budget_exceeded` con el total (`adapters/inbound/flow.py:148`, `:237-239`). Se comprueba después de `interval_too_short`. Decisión: [ADR 0016](../decisions/0016-instant-tier.md).
- Al enviar se crea la entry con `title = name` (`adapters/inbound/flow.py:638-673`).

### Datos guardados

`data = {host, port, unit_id, profile, components, intervals}` más `metering` si el perfil declara modos, y `device_id` y `serial_number` si los hay (`adapters/inbound/flow.py:649-663`). `intervals` lleva los cuatro tiers: los que no salen en el formulario conservan el valor por defecto. Claves en `const.py:5-12`.

## Entries de la versión 1

Hasta `0.1.0b2` había una entry por marca con un subentry por equipo (ADR [0004](../decisions/0004-entry-brand-subentry-device.md)). El flow es ahora `VERSION = 2` (`adapters/inbound/flow.py:308`). Una entry v1 no se migra: queda en `MIGRATION_ERROR` y el log dice «Modbus Solar now uses one entry per inverter instead of one per brand. Delete this entry and add each inverter again.» (`__init__.py:96-104`). Hay que borrarla y añadir cada equipo.

Una entry v2 creada antes del flujo de componentes no guarda `components`, `device_id` ni `serial_number`: toma todos los componentes del perfil (`select(profile, None)`, `application/selection.py:40`) y sus dispositivos y `entity_id` no llevan Device ID. El `unique_id` de la entry y el de las entidades no cambian.

Una entry sin `metering` toma el primer modo del perfil, «Consumos en Grid»: las energías de red siguen en Red con la misma fuente y solo se añaden Potencia de red y Potencia a la red (`__init__.py:75-77`, `application/selection.py:21-25`). No hay migración: el valor ausente tiene un significado fijo, y el flow sigue en `VERSION = 2`.

## Componentes y dispositivos

- Al cargar la entry, el runtime lee solo las entidades, energías y controles de los componentes elegidos, más las potencias y energías del modo de medición (`application/selection.py:48-72`, `__init__.py:67-89`).
- Los componentes elegidos incluyen siempre el principal, el vatímetro del modo y el dispositivo de sus entidades (`application/selection.py:33-45`).
- Las entidades y los dispositivos de los componentes no elegidos se borran del registro, con su historial. También las entidades de los otros modos de medición, y el dispositivo Generador si el modo no es «Aislada» (`__init__.py:28-64`).
- Cada componente es un dispositivo: el principal usa `(DOMAIN, entry_id)`; los demás, `(DOMAIN, f"{entry_id}_{componente}")` con `via_device` hacia el principal (`adapters/inbound/entities/base.py:17-36`).
- Plataformas: `sensor`, `binary_sensor`, `number` y `switch` (`__init__.py:25`). Los bits del BMS son `binary_sensor` (`adapters/inbound/entities/binary_sensor.py:11-24`).

## Reconfigure

Hasta cinco pasos (`adapters/inbound/flow.py:675-862`).

1. **`reconfigure` · conexión.** Cambia `host`, `port`, `unit_id`, `device_id` y `serial_number`. Prueba la conexión con la misma sonda del alta; si falla, no sigue ni guarda (`adapters/inbound/flow.py:675-715`). Recalcula el `unique_id` con el endpoint nuevo; si choca con otra entry del dominio, aborta con `already_configured` (`adapters/inbound/flow.py:685-687`). `device_id_in_use` e `invalid_serial_number` como en el alta.
2. **`reconfigure_metering`.** El mismo desplegable del alta, solo si el perfil declara modos. Por defecto, el modo guardado; sin él, el primero (`adapters/inbound/flow.py:707-708`, `:762-772`). La descripción avisa: entre «Consumos en Grid» y «Consumos en Cargas Críticas», las potencias y energías de red cambian de dispositivo y conservan su historial; al pasar a «Aislada» se borran con su historial; al salir de «Aislada» se borran las del generador.
3. **`reconfigure_components`.** Marca o desmarca los componentes. Sin la clave guardada (entry antigua) salen todos marcados (`adapters/inbound/flow.py:774-788`). Misma regla de componente forzado que el alta.
4. **`reconfigure_intervals`.** Igual que `intervals` del alta, con los valores guardados por defecto. Guarda también `metering` (`adapters/inbound/flow.py:790-833`, `:808-810`).
5. **`reconfigure_rename`.** Solo si cambia el Device ID. Muestra cuántas entidades se renombran, cuántas se mantienen y cuántas chocan; al confirmar renombra los `entity_id` que empiezan por el prefijo del ID viejo y guarda (`adapters/inbound/flow.py:249-303`, `:835-862`). Las que no siguen el patrón generado (por ejemplo, las que el usuario personalizó) se mantienen; si la entry no tenía ID, el ID viejo se muestra como «sin ID»; las que chocarían con un `entity_id` existente no se renombran.

Al final guarda y recarga la entry con `async_update_reload_and_abort`: la recarga abre la conexión con el endpoint nuevo y aplica los componentes y el modo de medición.

Mínimos del STORAGE 1Play TL M: 1,0 s por petición, bloques de 10 registros como máximo y huecos de hasta 9 registros leídos dentro del bloque (`profiles/ingeteam/oneplay_storage.py:197-200`):

| Tier | Bloques (direcciones del protocolo) | Mínimo |
|---|---|---|
| `instant` | 1 (69-71) | 1 s |
| `fast` | 6 (15-20, 28-37, 38-46, 48-54, 68, 78-80) | 6 s |
| `normal` | 5 (17-26, 29-35, 40-41, 57, 77) | 5 s |
| `slow` | 3 (6-7, 21-27, 59-60) | 3 s |

Dirección = registro − 30001. El mínimo cuenta todas las entidades del tier, también las deshabilitadas, y todo el perfil, aunque se hayan desmarcado componentes (`application/poller.py:46-49`).

Mínimos del 1Play TL M sin storage (`min_request_interval_s=1.0`, `profiles/ingeteam/oneplay.py:12`):

| Tier | Registros | Bloques | Mínimo |
|---|---|---|---|
| `fast` | `0x101D`, `0x1037` | 2 | 2 s |
| `normal` | `0x1021` | 1 | 1 s |

Sin entidades en `instant` ni en `slow`: el formulario no muestra esos tiers.

## Intervalos por defecto

`instant` 5 s, `fast` 10 s, `normal` 60 s, `slow` 3600 s (`const.py:15`). Decisiones: [ADR 0005](../decisions/0005-poll-tiers.md) y [ADR 0016](../decisions/0016-instant-tier.md).
