---
type: feature
area: config-flow
layers: [domain, application, adapters]
status: draft
date: 2026-10-04
---

# Spec 4 — Flujo de configuración v2: marca, modelo, componentes y ajustes después del alta

Rutas bajo `custom_components/modbus_solar/` salvo indicación.

## 1. Objetivo y alcance

La spec 2 ([setup-flow](../2026-10-04-setup-flow/spec.md)) dejó una entry por dispositivo con tres pasos:
modelo, conexión y confirmación. Esta spec la mejora según el mockup [proposal.html](proposal.html): marca,
modelo, errores, lecturas, nombre, Device ID, frecuencia de lectura, componentes por dispositivo, reconfigure y
bits del BMS.

Problemas que resuelve, con la referencia al código actual:

| # | Problema | Dónde |
|---|---|---|
| 1 | La lista de modelos no explica la diferencia entre ellos | `adapters/inbound/flow.py:89` |
| 2 | Jerga en los textos: «entry», «host», «endpoint» | `translations/es.json` |
| 3 | El campo de IP no dice dónde encontrarla; «Avanzado» no explica sus valores | `strings.json` → `config.step.connection` |
| 4 | El error de conexión no dice IP, puerto ni tiempo | `adapters/inbound/flow.py:110-111` |
| 5 | «Revisa el modelo», pero el modelo no se puede cambiar sin cerrar el flujo | `adapters/inbound/flow.py:112-113` |
| 6 | Lecturas en lista plana | `adapters/inbound/flow.py:55-70` |
| 7 | Sin vuelta atrás desde la confirmación | `adapters/inbound/flow.py:139-155` |
| 8 | Reconfigure no prueba la conexión ni cambia el Unit ID | `adapters/inbound/flow.py:157-200` |
| 9 | Intervalos mezclados con la conexión, sin el mínimo a la vista | `adapters/inbound/flow.py:163-165`, `:193` |
| 10 | Mezcla «equipo» e «inversor»; la integración cubre cualquier dispositivo solar | `translations/es.json` |
| 11 | Marca y modelo en una sola lista | `adapters/inbound/flow.py:88-92` |
| 12 | Un solo dispositivo con 47 entidades; no se puede quitar lo que la instalación no tiene | `adapters/inbound/entities/base.py:36-41` |
| 13 | Los bits del BMS (30029, 30069) no se leen | `profiles/ingeteam/oneplay_storage.py` |
| 14 | Dos equipos del mismo tipo dan dispositivos con el mismo nombre; el segundo solo se distingue por el sufijo `_2` del `entity_id` | `adapters/inbound/entities/base.py:36-41` |

**Dentro:**
- Paso de marca separado del de modelo, siguiendo `profiles/<marca>/`.
- Etiquetas de modelo traducidas.
- Paso de componentes: el usuario marca qué partes tiene la instalación.
- Un dispositivo de HA por componente, bajo la misma entry. La entry hace de hub.
- Ayudas por campo, errores con datos y vocabulario neutro («dispositivo»).
- Lecturas agrupadas por componente y menú de confirmación con vuelta a modelo o conexión.
- Paso de nombre propio, con número de serie opcional. Se lee por Modbus si el perfil declara su registro.
- Device ID: número que distingue equipos del mismo tipo en el nombre de sus dispositivos y en el `entity_id`
  (§5.6).
- Reconfigure en tres pasos: conexión (con sonda bloqueante, Unit ID y Device ID), componentes e intervalos. Un
  cuarto paso renombra los `entity_id` si cambia el Device ID.
- Paso de frecuencia de lectura en el alta y en reconfigure, con la lista de entidades de cada intervalo y su mínimo.
- Tier `instant` para la red, 5 s por defecto (§5.8).
- Bits del BMS de 30029 (Nota 4) y 30069 (Nota 10), en «Batería» (§5.3).

**Fuera:**
- Interpretar el signo con texto («exportando»): los signos no están verificados
  (`docs/features/monitoring.md`, «Signos supuestos»).
- Detectar el modelo real del dispositivo o sus componentes.
- Descubrimiento automático (DHCP, zeroconf).
- Configurar el control de vertido durante el alta: el estado inicial es optimista (ADR 0012).
- Migrar datos de entries: ver §8.
- Registros de número de serie en los perfiles de Ingeteam: sus mapas no lo documentan
  (`docs/wiki/brands/ingeteam/*/registers*.md`).
- Etiquetas de los motivos (Notas 7, 8 y 9): spec 5, [reason-labels](../2026-10-04-reason-labels/spec.md).
- Paradas y alarmas del inversor (30010, 30011, 30013-30015): su tabla solo está en `ABH2010IMC14`, que no
  está en el repo (`docs/wiki/brands/ingeteam/README.md`).
- Registros 30074-30077 (Nota 11): fuera hasta tener su tabla extraída.

## 2. Decisiones

| Tema | Decisión |
|---|---|
| Paso de marca | Se muestra siempre, aunque solo haya una marca |
| Volver tras un error de conexión | El formulario añade el campo «Modelo» tras el error (§3.3). Cambiar de marca exige cerrar el flujo |
| Descripción del modelo | `translation_key` en el selector. El perfil no cambia |
| Componentes | Paso 4 del alta, tras la conexión y antes de las lecturas, con casillas. El componente principal va siempre y no sale en la lista |
| Dispositivos | Uno por componente. La entry hace de hub con su título. Los dispositivos llevan nombre corto («Batería») y `via_device` hacia el principal (ADR 0015) |
| Límite de vertido | En el dispositivo principal: es un comando al inversor aunque actúe sobre la red |
| Bits del BMS | En «Batería». Un `binary_sensor` por bit (§5.3) |
| Tier y activación de las extras | Los de la wiki del modelo, «Tier y activación de las entidades de diagnóstico» (§5.7) |
| Intervalo rápido por defecto | 10 s en todos los perfiles. Con §5.7 la rápida del STORAGE pide 6 bloques: 6 s de mínimo, por encima de los 5 s de hoy |
| Tier instantáneo | Tier nuevo `instant` («Instantánea»), 5 s por defecto. Solo la red: tensión, frecuencia y potencia (30070-30072), más las energías de red. Los intervalos, juntos, no pasan de una petición por segundo (§5.8) |
| Entries anteriores | Las extras siguen desactivadas: el registro de entidades conserva `disabled_by`. Sin migración |
| Device ID | Entero ≥ 0, obligatorio en el alta, único por `device_type`. Va detrás del nombre de cada dispositivo de la entry («Batería 0») y de ahí pasa al `entity_id`. Cambiarlo en reconfigure renombra los `entity_id` generados (§5.6) |
| Reconfigure | Tres pasos: conexión, componentes e intervalos, más un cuarto si cambia el Device ID. La conexión se prueba; si falla, no sigue ni guarda |
| Intervalos | Último paso del alta, después de los componentes, y último paso de reconfigure. Siguen en `entry.data`. Sin options flow |
| Lista de entidades por intervalo | Una `section` plegada por intervalo, con la lista en el `data_description` de su campo |
| Vocabulario | Los textos del flujo dicen «dispositivo», nunca «inversor». Los nombres de componente son datos del perfil |

## 3. Flujo de alta

`DeviceConfigFlow` en `adapters/inbound/flow.py`. Sigue con `VERSION = 2` (§8).

Pasos: `user` (marca) → `model` → `connection` → `components` → `readings` (menú) → `name` → `intervals`.

### 3.1 Paso `user` — marca

- Campo `brand`: `SelectSelector` en modo `list`, sin valor por defecto.
- Opciones: `catalog.brands()` (`application/catalog.py:16-17`). Etiqueta: `BRAND_TITLES[brand]` (`const.py:12`).
- Texto: «Elige la marca» / «Marca del dispositivo que quieres añadir. Suele estar en la etiqueta o en el
  frontal.»
- Se muestra aunque `catalog.brands()` devuelva una sola marca.

La marca sale del campo `brand` de cada perfil, no del nombre de la carpeta. Un test de catálogo nuevo
comprueba que el `brand` de cada perfil coincide con su carpeta en `profiles/`. Hoy ningún test lo hace: en
`tests/` solo hay `tests/unit/test_profiles.py:68-70`, que mira el catálogo.

### 3.2 Paso `model` — modelo de la marca

- Campo `profile`: `SelectSelector` en modo `list`, sin valor por defecto, con
  `translation_key="profile"`.
- Opciones: `catalog.for_brand(brand)` (`application/catalog.py:19-20`). `value` = id del perfil.
- Etiqueta traducida en `strings.json` → `selector.profile.options.<id>`. El id lleva punto
  (`ingeteam.oneplay_storage`); si las claves de traducción no lo admiten, se usa el id con `_` en lugar de
  `.` como clave y como `value`. Se resuelve en el plan con un test.
- Etiquetas iniciales:

| Perfil | en | es |
|---|---|---|
| `ingeteam.oneplay` | 1Play TL M — PV inverter, no battery | 1Play TL M — inversor solo fotovoltaico, sin batería |
| `ingeteam.oneplay_storage` | STORAGE 1Play TL M — hybrid inverter with battery | STORAGE 1Play TL M — inversor híbrido, con batería |

- Texto: «¿Qué modelo de {brand}?» / «Busca el modelo en la etiqueta del dispositivo. Si tienes varios,
  añade uno y repite.»
- `tests/unit/test_translations.py` comprueba que cada perfil de `ALL_PROFILES` tiene su etiqueta.
- Al enviar, pasa a `connection`.

### 3.3 Paso `connection` — conexión

Igual que hoy (`adapters/inbound/flow.py:96-137`) salvo los textos y los errores:

- `host` con etiqueta «Dirección IP» y `data_description`: «Está en el menú de comunicaciones del dispositivo
  o en la lista de dispositivos de tu router.»
- Sección `advanced`, plegada: «Opciones avanzadas», con `data_description` «Cámbialos solo si los cambiaste
  en el dispositivo.»
- Descripción con placeholders `{brand}`, `{model}` y `{timeout}` (`PROBE_TIMEOUT_S`, `adapters/inbound/flow.py:48`).
- El control de duplicados y la sonda no cambian (`adapters/inbound/flow.py:103-113`).
- Al sondear bien, si el perfil tiene componentes opcionales (§5.1), pasa a `components`. Si no, pasa a `readings`.

Errores, con placeholders `{host}`, `{port}` y `{timeout}`:

| Clave | Texto (es) |
|---|---|
| `cannot_connect` | No responde en {host}:{port} tras {timeout} s. Comprueba la IP, activa Modbus TCP en el dispositivo y cierra otros clientes Modbus, como el EMS. |
| `invalid_response` | Respuesta inesperada de {host}:{port}. Puede que el modelo o el Unit ID no sean los correctos. |
| `endpoint_in_use` | Otro dispositivo ya usa esta IP y este puerto con otra configuración. |

`cannot_connect` incluye el tiempo agotado y el `DeviceUnavailable`, como hoy.

**Campo «Modelo» tras el error.** Tras cualquier error, el esquema añade el campo `profile`
con los modelos de la marca y el actual como valor. Al reenviar, si el modelo cambió, se usa el nuevo perfil
y sus puertos por defecto solo si el usuario no tocó los avanzados. Cambiar la marca exige cerrar el flujo.

### 3.4 Paso `readings` — lecturas y menú

`async_show_menu(step_id="readings", menu_options=[…], description_placeholders=…)`.

- Descripción: «✓ Responde en {host}. Comprueba que estos valores cuadran con la pantalla del dispositivo:» y
  `{readings}`.
- Opciones:
  - «Valores correctos: continuar» → `name`;
  - «Cambiar el modelo» → `model`;
  - «Cambiar la conexión» → `connection`, con los valores anteriores.
- Al volver a `model` o `connection` se olvidan las lecturas y el `unique_id` se recalcula al reenviar. Al volver
  a `model` se olvidan también los componentes elegidos.

`format_readings` (`adapters/inbound/flow.py:55-70`) agrupa por componente:

- Primero el principal, después los opcionales elegidos en `components`, en el orden del perfil.
- Solo las entidades activas del principal y de los componentes elegidos. Sin componentes opcionales en el perfil,
  las de todo el perfil.
- La sonda lee los tiers `fast` e `instant` (§5.8), para que la red salga en las lecturas.
- Solo entidades `sensor`. Los bits del BMS (§5.3) no salen: la sonda los lee porque son `fast` y activos
  (`application/probe.py:16`), pero no se cotejan con la pantalla. Hoy `format_readings` busca el nombre en
  `entity.sensor` (`adapters/inbound/flow.py:57`, `:69`): sin filtro saldrían como `bms_alarm_…: False`.
- Título de cada grupo: el nombre traducido del dispositivo (§5.2), vía `async_get_translations`, como los
  nombres de entidad hoy (`adapters/inbound/flow.py:116`).
- Un grupo sin lecturas no aparece.
- Los números con separador de miles según `hass.config.language`. El signo se muestra tal cual.
- Un valor sin decodificar sigue mostrando `—`.

### 3.5 Paso `name` — nombre, número de serie y Device ID

Campos en este orden: nombre, Device ID y número de serie, como en la maqueta.

- Campo `name`, obligatorio. Por defecto `"{marca} {primer modelo}"`, como hoy (`adapters/inbound/flow.py:150`).
  Es el título de la entry, que agrupa los dispositivos en la página de la integración.
  `data_description`: «Así se llama el grupo de dispositivos en Home Assistant. Se puede cambiar después.»
- Campo `device_id`, obligatorio, `NumberSelector` en modo caja, mínimo 0, paso 1. Por defecto, el menor entero
  libre entre las entries del mismo `device_type` (§5.6). Si está ocupado, el error `device_id_in_use` con
  placeholders: «Ya hay un {device_type} con el ID {device_id}.», con el nombre traducido del tipo en
  minúscula. El paso no avanza hasta que el ID esté libre.
  `data_description`: «Identificador interno de la integración. Distingue equipos del mismo tipo. No tiene nada
  que ver con el Unit ID de Modbus.»
- Campo `serial_number`, opcional, `TextSelector`. Solo letras y números, sin espacios a los lados; otro valor da
  el error `invalid_serial_number`. `data_description` con placeholder según el perfil:
  - con registro de serie y valor leído: «Déjalo vacío: este modelo lo envía por Modbus. Leído: {serial}.»;
  - con registro pero sin lectura válida: «Este modelo lo envía por Modbus, pero no se ha podido leer. Cópialo de
    la etiqueta.»;
  - sin registro: «Este modelo no lo envía por Modbus. Cópialo de la etiqueta del dispositivo.»
- Al enviar, pasa a `intervals`.
- Creación de la entry, que hace el último paso del alta (§3.6): `async_create_entry` con los datos de
  hoy (`adapters/inbound/flow.py:142-149`) más `components` (§3.7), los intervalos de §3.6, `device_id` y
  `serial_number`: el valor escrito; si está vacío, el leído; si no hay ninguno, la clave no se guarda.

### 3.6 Paso `intervals` — frecuencia de lectura

- Mismo formulario que `reconfigure_intervals` (§4.3): una `section` plegada por tier con su campo `interval`,
  su mínimo y la lista de entidades (§4.4) en el `data_description`.
- Valores por defecto: `DEFAULT_INTERVALS` (`const.py:10`), que pasa a `instant` 5, `fast` 10, `normal` 60 y
  `slow` 3600 s (§5.7, §5.8).
- Los componentes ya están elegidos (§3.7): la lista de cada tier lleva solo las entidades del principal y de los
  componentes elegidos, y aparecen los tiers que tengan entidades así.
- Validación de mínimo como en reconfigure: `interval_too_short` si el valor es menor que `min_tier_interval`
  (`application/poller.py:46`).
- Validación de presupuesto como en reconfigure: `interval_budget_exceeded` (§5.8).
- Al enviar, crea la entry (§3.5). Con `components` vacío en un perfil sin componentes opcionales, como
  `ingeteam.oneplay`.
- Un tier que se quede sin entidades tras elegir componentes guarda su intervalo igualmente; no crea coordinator
  (`adapters/inbound/runtime.py:68-85`).

### 3.7 Paso `components` — qué tiene la instalación

- Campo `components`: `SelectSelector` con `multiple=True`, modo `list` (casillas), con
  `translation_key="component"`.
- Opciones: los componentes opcionales del perfil (§5.1), en su orden. `value` = valor de `Component`.
- Paso 4 del alta, tras la conexión. Va antes de las lecturas y de los intervalos para que ambos solo lleven los
  componentes elegidos, y después de la sonda para que el usuario elija sabiendo ya que el dispositivo responde.
- Si el perfil no tiene componentes opcionales, el paso se salta.
- Valor por defecto: los que el perfil marca `default=True`.
- Puede quedar vacío: solo se crea el dispositivo principal.
- Texto: «¿Qué tiene tu instalación?» / «{model}. {main} se añade siempre. Marca el resto de partes que
  tiene tu instalación: cada una sale en Home Assistant como un dispositivo propio. Se puede cambiar después
  en «Reconfigurar».»
  - `{main}`: nombre traducido del componente principal (§5.2), por ejemplo «Inversor».
- Etiqueta de cada opción, en `selector.component.options.<valor>`, con su contenido:

| Componente | es |
|---|---|
| `pv` | Campo solar — FV1, FV2 y FV externa |
| `battery` | Batería — carga, salud, motivos de limitación y alarmas del BMS |
| `grid` | Red (vatímetro externo) — tensión, frecuencia, potencia y energías de red |
| `internal_meter` | Vatímetro interno |
| `critical_loads` | Cargas críticas — salida de respaldo |
| `load` | Consumo — consumo total de la casa |
| `ev_charger` | Cargador VE |

`SelectOptionDict` no tiene subtítulo: nombre y contenido van en la misma etiqueta, como en §3.2.

- Al enviar, pasa a `readings`.

### 3.8 Número de serie por Modbus

- `DeviceProfile` gana `serial: RegisterSpec | None = None` (`domain/profile.py:36-50`). Ningún perfil lo
  declara hoy.
- `DataType` (`domain/types.py:6-10`) solo tiene enteros. Se añade un tipo de texto ASCII de N registros,
  con su longitud en `RegisterSpec`, y su decodificación en `domain/decode.py`. Bytes nulos y espacios finales
  se recortan. La forma exacta se fija en el plan.
- `domain/validate.py` comprueba que `serial`, si existe, usa ese tipo.
- La sonda (`application/probe.py`) lee el registro de serie si existe. Un fallo en esa lectura no hace fallar la
  sonda: el número queda vacío.
- `DeviceInfo` del dispositivo principal pasa `serial_number` desde `entry.data`. Los demás dispositivos no lo
  llevan.
- Diagnósticos: `serial_number` se añade a `TO_REDACT`, junto al host (`adapters/inbound/diagnostics.py:11`).

## 4. Reconfigure — conexión, componentes e intervalos

Tres pasos, más un cuarto si cambia el Device ID (§4.5). Los cambios solo se guardan al final del último.

### 4.1 Paso `reconfigure` — conexión

- `host` y sección `advanced` plegada con `port` y `unit_id`. Hoy el `unit_id` no se puede cambiar
  (`adapters/inbound/flow.py:168`).
- Campo `serial_number`, opcional, relleno con el valor guardado. Mismas reglas que en §3.5. El formulario sale
  antes de la sonda, así que la ayuda no lleva valor leído: con registro de serie, «Déjalo vacío para leerlo
  por Modbus.»; sin registro, el texto de §3.5.
- Campo `device_id`, relleno con el valor guardado. Mismas reglas que en §3.5, sin contar la propia entry. En una
  entry sin `device_id` (creada antes de v2) sale vacío y es opcional: si sigue vacío, la entry sigue sin ID.
- Botón «Probar y seguir». Al enviar, en este orden:
  1. Si otra entry tiene el `unique_id` nuevo: aborta con `already_configured`, como hoy
     (`adapters/inbound/flow.py:169-172`).
  2. Valida el Device ID. Con `device_id_in_use`, el formulario vuelve sin probar.
  3. Sonda con el perfil de la entry y `PROBE_TIMEOUT_S`. Con error, el formulario vuelve con los errores de §3.3.
  4. Con éxito, guarda la conexión, el número de serie y el Device ID en el flujo y pasa a
     `reconfigure_components`, o a `reconfigure_intervals` si el perfil no tiene componentes opcionales. El número
     de serie se resuelve como en §3.5 con la lectura de esta sonda: escrito; si está vacío, el leído; si no hay
     ninguno, se quita de `data`.

### 4.2 Paso `reconfigure_components` — componentes

- Mismo campo y textos que §3.7. Valor por defecto: `entry.data["components"]`, o todos los opcionales del perfil
  si la clave falta (§8).
- Va antes de los intervalos porque la lista de entidades de cada intervalo depende de los componentes.
- Al desmarcar un componente, sus entidades y su dispositivo se borran del registro al recargar (§5.5). El
  historial de las entidades borradas se pierde. La descripción lo avisa: «Lo que desmarques se quita de Home
  Assistant con su historial.»

### 4.3 Paso `reconfigure_intervals` — frecuencia de lectura

- Una `section` plegada por tier, con clave `tier.value` y un campo `interval` dentro. HA no anida sections
  («Only a single level of sections is allowed», developers.home-assistant.io/docs/data_entry_flow_index), así
  que este paso va aparte del de conexión, que ya usa la sección `advanced`.
- Solo aparecen los tiers con entidades de los componentes elegidos: `build_runtime` solo crea coordinators para
  los tiers con entidades (`adapters/inbound/runtime.py:68-85`). En `ingeteam.oneplay` no hay tier `slow`.
- Valores por defecto: los de `entry.data[CONF_INTERVALS]`, completados con `DEFAULT_INTERVALS` (`const.py:10`).
- `data_description` del campo de cada tier: resumen, mínimo y lista de entidades (§4.4), con placeholders.
- Validación de mínimo como hoy: `interval_too_short` si el valor es menor que `min_tier_interval`
  (`application/poller.py:46`; `adapters/inbound/flow.py:163-165`). Una entry STORAGE anterior trae `fast` 5 s
  guardado y el mínimo nuevo es 6 s: el paso da el error hasta que el usuario lo sube (§5.7).
- El mínimo cuenta el perfil entero: también las entidades desactivadas y las de componentes no marcados
  (`application/poller.py:46-49`). Puede ser mayor que lo que se lee de verdad. En el STORAGE no cambia nada:
  la rápida da 6 bloques con cualquier selección, por las extras del Inversor (30039, 30040, 30055) y los bits
  del BMS, que van siempre.
- Validación de presupuesto: con todos los mínimos cumplidos, `interval_budget_exceeded` si los intervalos, juntos,
  pasan de una petición por segundo (§5.8). Error del formulario entero, no de un campo.
- Al enviar, si el Device ID ha cambiado, pasa a `reconfigure_rename` (§4.5) sin guardar. Si no:
  `async_update_reload_and_abort(entry, unique_id=…, data=…)` con la `data` completa de la entry:
  conexión, número de serie, Device ID, componentes e intervalos nuevos. Se usa `data` y no `data_updates` porque un número
  de serie vaciado sin lectura tiene que desaparecer de la entry.
  Los intervalos siguen en `entry.data[CONF_INTERVALS]`, como hoy.

### 4.4 Lista de entidades por tier

Se genera desde el perfil y los componentes elegidos: para cada tier, las entidades con ese `poll`, con su
nombre traducido. Va en este orden:

1. Entidades leídas, agrupadas por componente. Las que tienen `enabled_default=False` llevan «(desactivada)».
2. Energías calculadas cuyas fuentes son de ese tier (`DeviceProfile.energies`; mismo tier exigido por
   `domain/validate.py:60-72`).
3. Controles, en el tier de `probe_key` (`adapters/inbound/entities/factory.py:50-53`).

Con el nombre corto (§5.4), cada entidad lleva delante su dispositivo: «Batería · Estado de carga».

Para `ingeteam.oneplay_storage` con todos los componentes, con el tier y la activación de §5.7 y §5.8: instant 3 +
2 energías; fast 34 + 3 energías + 2 controles, 4 desactivadas; normal 12, 5 desactivadas; slow 6, 4 desactivadas.

La documentación de HA recoge placeholders en la descripción del paso, no en la de una section. Por eso la
lista va en el `data_description` del campo y no en la descripción de la section.

### 4.5 Paso `reconfigure_rename` — renombrar entidades

Solo sale si el Device ID de §4.1 es distinto del guardado, incluido pasar de sin ID a con ID.

- Se calcula sobre las entidades de la entry en el registro de entidades (`er.async_entries_for_config_entry`).
  Las de otras entries no se miran.
- Prefijo generado de cada entidad: `<plataforma>.<slug del nombre de su dispositivo con el ID guardado>_`, por
  ejemplo `sensor.bateria_0_`. Sin ID guardado, `sensor.bateria_`. El nombre del dispositivo es el de §5.2,
  traducido con `async_get_translations` en `hass.config.language`, no el que el usuario haya puesto en HA.
- Para cada entidad:
  - **se renombra** si su `entity_id` empieza por el prefijo: se cambia solo el prefijo, por el del ID nuevo
    (`sensor.bateria_0_tension` → `sensor.bateria_2_tension`);
  - **se mantiene** si no empieza por el prefijo: el usuario lo personalizó, o la entidad se creó antes de v2
    con otro nombre de dispositivo;
  - **choca** si el `entity_id` nuevo ya existe en el registro: no se renombra.
- Formulario sin campos, con botón «Confirmar». Descripción con placeholders: ID viejo y nuevo, número de
  renombradas con hasta tres ejemplos, número de mantenidas y lista de las que chocan. Para cancelar se cierra el
  diálogo: no se guarda nada.
- Al confirmar, en este orden:
  1. `er.async_get(hass).async_update_entity(entity_id, new_entity_id=…)` para cada entidad que se renombra.
  2. `async_update_reload_and_abort(entry, unique_id=…, data=…)`, como §4.3. Al recargar, los dispositivos
     toman el nombre con el ID nuevo.
- El historial sigue a la entidad: va por `unique_id`, que no cambia (`adapters/inbound/entities/base.py:30`).
- Las automatizaciones, tarjetas y plantillas que usen el `entity_id` viejo no se actualizan. La descripción lo
  avisa: «Revisa las automatizaciones y tarjetas que usen los nombres viejos.»

## 5. Componentes y dispositivos

### 5.1 Dominio

- `Component` (StrEnum, `domain/types.py`): `main`, `pv`, `battery`, `grid`, `internal_meter`,
  `critical_loads`, `load`, `ev_charger`.
- `EntitySpec`, `EnergySpec` y `GatedLimitSpec` ganan `component: Component = Component.MAIN`. Con el valor por
  defecto, `ingeteam.oneplay` no cambia.
- `DeviceProfile` gana `components: tuple[ComponentSpec, ...] = ()`: los opcionales, en orden.
  `ComponentSpec(component: Component, default: bool = True)`. `main` no va en la lista: está siempre.
- `domain/validate.py` comprueba:
  - que todo `component` distinto de `main` está en `components`;
  - que `components` no repite ni incluye `main`;
  - que cada componente declarado tiene al menos una entidad;
  - que una energía va en el componente de sus fuentes.
- `application/` ofrece una función pura que, dado un perfil y una selección, devuelve sus entidades, energías y
  controles. La usan el runtime, `format_readings` y la lista de §4.4.

Reparto de `ingeteam.oneplay_storage` (`profiles/ingeteam/oneplay_storage.py`):

| Componente | en | Por defecto | Entidades | N.º hoy |
|---|---|---|---|---|
| `main` (Inversor) | Inverter | siempre | `inverter_state`, `active_power`, `operation_time`, `reactive_power`, `power_factor`, `power_reduction_ratio`, `power_reduction_reason`, `dc_bus_voltage`, `inverter_temperature`, `isolation_positive`, `isolation_negative`, `export_limit`, `export_enabled` | 13 |
| `pv` (Campo solar) | Solar array | sí | `pv1_voltage`, `pv1_current`, `pv1_power`, `pv2_voltage`, `pv2_current`, `pv2_power`, `external_pv_power`, `solar_energy` | 8 |
| `battery` (Batería) | Battery | sí | `battery_voltage`, `battery_current`, `battery_power`, `battery_soc`, `battery_soh`, `battery_state`, `battery_temperature`, `battery_charge_limit_reason`, `battery_discharge_limit_reason`, `battery_charge_energy`, `battery_discharge_energy` | 11 |
| `grid` (Red) | Grid | sí | `grid_voltage`, `grid_frequency`, `grid_power`, `grid_import_energy`, `grid_export_energy` | 5 |
| `internal_meter` (Vatímetro interno) | Internal meter | no | `internal_meter_voltage`, `internal_meter_current`, `internal_meter_frequency`, `internal_meter_power` | 4 |
| `critical_loads` (Cargas críticas) | Critical loads | sí | `critical_load_voltage`, `critical_load_current`, `critical_load_frequency`, `critical_load_power` | 4 |
| `load` (Consumo) | Load | sí | `load_power` | 1 |
| `ev_charger` (Cargador VE) | EV charger | no | `ev_charger_power` | 1 |

«Solar array» y no «PV array»: las entidades `pv1_*`, `pv2_*` y `external_pv_power` ya dicen «PV» en inglés
(`translations/en.json`), y «PV array PV1 voltage» lo repetiría.

Total: 47, las de hoy. El cambio `reason-labels` suma 1 a `main` (30043, Nota 8). Los bits del BMS suman 14 a
`battery` (§5.3).

`ingeteam.oneplay` no declara componentes: sus 3 entidades van en `main`.

### 5.2 Dispositivos en HA

`ModbusSolarEntity` (`adapters/inbound/entities/base.py:36-41`) construye el `DeviceInfo` según el componente:

| | Principal (`main`) | Opcional |
|---|---|---|
| `identifiers` | `{(DOMAIN, entry_id)}`, como hoy | `{(DOMAIN, f"{entry_id}_{component}")}` |
| Nombre | `translation_key` = `device_type` del perfil (`domain/profile.py:40`), por ejemplo `inverter` → «Inversor»; con Device ID, `inverter_numbered` → «Inversor 0» | `translation_key` = valor del componente; con Device ID, `<componente>_numbered` |
| `translation_placeholders` | `{"device_id": "0"}` con Device ID; sin él, nada | igual |
| `via_device` | — | `(DOMAIN, entry_id)` |
| `manufacturer`, `model` | como hoy | como hoy |
| `serial_number` | de `entry.data` (§3.8) | — |

- Nombres en `strings.json` → `device.<clave>.name`. es: Inversor, Campo solar, Batería, Red, Vatímetro interno,
  Cargas críticas, Consumo, Cargador VE. en: Inverter, Solar array, Battery, Grid, Internal meter, Critical loads,
  Load, EV charger (§5.1).
- Cada clave tiene su par `<clave>_numbered` con el placeholder detrás: «Batería {device_id}» / «Battery
  {device_id}». Las entries sin Device ID usan la clave sin placeholder (§5.6).
- El dispositivo principal deja de llamarse como la entry (`name=runtime.title`). El título de la entry agrupa
  los dispositivos en la página de la integración: hace de hub.
- `manifest.json`: `integration_type` pasa de `device` a `hub`, porque una entry da varios dispositivos
  (ADR 0015).

### 5.3 Bits del BMS

Un `binary_sensor` por bit: 14 entidades en «Batería». Cada bit se automatiza y se notifica con un disparador
de estado `on`/`off`, sin buscar dentro de un texto, y lleva nombre traducido.

- `Platform` (`domain/types.py`) gana `BINARY_SENSOR`. `PLATFORMS` (`__init__.py:21`) gana
  `HaPlatform.BINARY_SENSOR`.
- `EntitySpec` gana `bit: int | None = None`. `decode` (`domain/decode.py`) devuelve `bool` si hay `bit`.
- `domain/validate.py`:
  - `bit` exige `platform` `binary_sensor`, tipo `U16` y `0 ≤ bit ≤ 15`, y al revés;
  - el control de solape (`domain/validate.py:81-82`) admite varias entidades sobre el mismo registro si todas
    llevan `bit`. `plan_blocks` ya quita registros repetidos (`domain/blocks.py:19`).
- Entidad nueva en `adapters/inbound/entities/` para `binary_sensor`, desde la misma fábrica.
- `Role` (`domain/types.py:33-60`) gana `BMS_ALARM` y `BMS_FLAG`: las 9 alarmas de 30029 llevan `BMS_ALARM`;
  los 5 flags de 30069, `BMS_FLAG`. No `DIAGNOSTIC` (`:53`): el `role` dice qué significa la medida sin
  depender de la marca, y otro perfil con BMS puede declarar los suyos con el mismo `role`. Hoy ningún código
  lee el `role`; no forma parte del `unique_id` (`adapters/inbound/runtime.py:33-35`).

Entidades, todas con `component=battery` y `entity_category` `diagnostic`. Fuente: `ABH2010IMB08` rev. _I,
págs. 6-8.

| Registro | Bit | Clave | Texto del PDF | es | en | `device_class` |
|---|---|---|---|---|---|---|
| 30029 | 0 | `bms_alarm_high_charge_current` | High Current Charge | Alarma: corriente de carga alta | Alarm: high charge current | `problem` |
| 30029 | 1 | `bms_alarm_high_voltage` | High Voltage | Alarma: tensión alta | Alarm: high voltage | `problem` |
| 30029 | 2 | `bms_alarm_low_voltage` | Low Voltage | Alarma: tensión baja | Alarm: low voltage | `problem` |
| 30029 | 3 | `bms_alarm_high_temperature` | High Temperature | Alarma: temperatura alta | Alarm: high temperature | `problem` |
| 30029 | 4 | `bms_alarm_low_temperature` | Low Temperature | Alarma: temperatura baja | Alarm: low temperature | `problem` |
| 30029 | 5 | `bms_alarm_internal` | BMS Internal | Alarma: fallo interno del BMS | Alarm: BMS internal fault | `problem` |
| 30029 | 6 | `bms_alarm_cell_imbalance` | Cell Imbalance | Alarma: desequilibrio de celdas | Alarm: cell imbalance | `problem` |
| 30029 | 7 | `bms_alarm_high_discharge_current` | High Current Discharge | Alarma: corriente de descarga alta | Alarm: high discharge current | `problem` |
| 30029 | 8 | `bms_alarm_system_error` | System BMS Error | Alarma: error del sistema BMS | Alarm: BMS system error | `problem` |
| 30069 | 0 | `bms_stop_charge` | Stop Charge | Carga bloqueada | Charge blocked | — |
| 30069 | 1 | `bms_stop_discharge` | Stop Discharge | Descarga bloqueada | Discharge blocked | — |
| 30069 | 2 | `bms_forced_charge` | Forced Charge (BMS) | Carga forzada por el BMS | Forced charge by BMS | — |
| 30069 | 3 | `bms_calibration` | Calibration | Calibración de SOC pendiente | SOC calibration pending | — |
| 30069 | 4 | `bms_forced_charge_soc` | Forced Charge (SOC) | Carga forzada por SOC bajo | Forced charge due to low SOC | — |

Tier `fast` y `enabled_default=True` en los 14, sin pasar por `_extra`. Tier y activación de las demás
entidades de diagnóstico: §5.7.

- Retraso de aviso: hasta 10 s en `fast` con el intervalo por defecto (§5.7), frente a hasta 1 h en `slow`. En
  `slow` una alarma corta puede no verse nunca.
- `enabled_default=False` obligaría a activar 14 entidades a mano antes de poder automatizar o notificar.
- `entity_category` `diagnostic` las deja fuera del panel generado por HA; siguen en la página del dispositivo.
- Bloques del tier `fast`: §5.7.

### 5.4 Nombres de entidad

Con `has_entity_name` (`adapters/inbound/entities/base.py:16`), HA antepone el nombre del dispositivo. Para no
repetir, los nombres de entidad se acortan dentro de su componente. Las claves no cambian.

Decidido el 5 de octubre de 2026: la entidad no repite su dispositivo. Maqueta: [naming.html](naming.html).
Nombres actuales de `translations/es.json` y `translations/en.json`. El `entity_id` que resulta para cada registro
está en la [wiki del modelo](../../wiki/brands/ingeteam/storage-1-play-tl-m/registers-storage-1-play-tl-m.md), columna `entity_id`.

| # | Dispositivo | Clave | Hoy (es) | Nuevo (es) | Hoy (en) | Nuevo (en) |
|---|---|---|---|---|---|---|
| 1 | Inversor | `inverter_state` | Estado del inversor | Estado | Inverter state | State |
| 2 | Inversor | `inverter_temperature` | Temperatura del inversor | Temperatura | Inverter temperature | Temperature |
| 3 | Batería | `battery_voltage` | Tensión de la batería | Tensión | Battery voltage | Voltage |
| 4 | Batería | `battery_current` | Corriente de la batería | Corriente | Battery current | Current |
| 5 | Batería | `battery_power` | Potencia de la batería | Potencia | Battery power | Power |
| 6 | Batería | `battery_soc` | Estado de carga de la batería | Estado de carga | Battery state of charge | State of charge |
| 7 | Batería | `battery_soh` | Estado de salud de la batería | Estado de salud | Battery state of health | State of health |
| 8 | Batería | `battery_state` | Estado de la batería | Estado | Battery state | State |
| 9 | Batería | `battery_temperature` | Temperatura de la batería | Temperatura | Battery temperature | Temperature |
| 10 | Batería | `battery_charge_energy` | Energía de carga de la batería | Energía de carga | Battery charge energy | Charge energy |
| 11 | Batería | `battery_discharge_energy` | Energía de descarga de la batería | Energía de descarga | Battery discharge energy | Discharge energy |
| 12 | Red | `grid_voltage` | Tensión de red | Tensión | Grid voltage | Voltage |
| 13 | Red | `grid_frequency` | Frecuencia de red | Frecuencia | Grid frequency | Frequency |
| 14 | Red | `grid_power` | Potencia de red | Potencia | Grid power | Power |
| 15 | Red | `grid_import_energy` | Energía importada de red | Energía importada | Grid import energy | Import energy |
| 16 | Red | `grid_export_energy` | Energía exportada a red | Energía exportada | Grid export energy | Export energy |
| 17 | Vatímetro interno | `internal_meter_voltage` | Tensión del vatímetro interno | Tensión | Internal meter voltage | Voltage |
| 18 | Vatímetro interno | `internal_meter_current` | Corriente del vatímetro interno | Corriente | Internal meter current | Current |
| 19 | Vatímetro interno | `internal_meter_frequency` | Frecuencia del vatímetro interno | Frecuencia | Internal meter frequency | Frequency |
| 20 | Vatímetro interno | `internal_meter_power` | Potencia del vatímetro interno | Potencia | Internal meter power | Power |
| 21 | Cargas críticas | `critical_load_voltage` | Tensión de cargas críticas | Tensión | Critical loads voltage | Voltage |
| 22 | Cargas críticas | `critical_load_current` | Corriente de cargas críticas | Corriente | Critical loads current | Current |
| 23 | Cargas críticas | `critical_load_frequency` | Frecuencia de cargas críticas | Frecuencia | Critical loads frequency | Frequency |
| 24 | Cargas críticas | `critical_load_power` | Potencia de cargas críticas | Potencia | Critical loads power | Power |
| 25 | Consumo | `load_power` | Potencia de consumo | Potencia | Load power | Power |
| 26 | Cargador VE | `ev_charger_power` | Potencia del cargador VE | Potencia | EV charger power | Power |
| 27 | Batería | `battery_charge_limit_reason` | Motivo de limitación de carga | sin cambio | Battery charge limit reason | Charge limit reason |
| 28 | Batería | `battery_discharge_limit_reason` | Motivo de limitación de descarga | sin cambio | Battery discharge limit reason | Discharge limit reason |
| 29 | Campo solar | `solar_energy` | Energía solar | Energía FV | Solar energy | PV energy |
| 30 | Inversor | `power_reduction_ratio` | Reducción de potencia | Ratio de reducción de potencia | Power reduction ratio | sin cambio |

Las filas 27 y 28 solo cambian en inglés: en español ya no repiten el dispositivo. La fila 30 solo cambia en
español: alinea el nombre con el inglés y lo separa de «Motivo de reducción de potencia». Las entidades FV
(`pv1_*`, `pv2_*`) se quedan como están: «Tensión FV1» / «PV1 voltage». El resto de entidades no cambia.

- En HA se ven con el dispositivo y su Device ID delante: «Batería 0 Estado de carga», «Red 0 Potencia». Sin
  Device ID (entries anteriores a v2): «Batería Estado de carga».
- La tarjeta de dispositivo muestra solo el nombre de la entidad: salen varias filas «Potencia» si se mezclan
  dispositivos en una misma tarjeta.

- El `entity_id` de una entidad ya creada no cambia: HA lo guarda en el registro.
- Una entidad nueva toma el `entity_id` del dispositivo, con su Device ID, y su nombre:
  `sensor.bateria_0_estado_de_carga`. Un segundo inversor con ID 1 da `sensor.bateria_1_estado_de_carga`, sin
  sufijo `_2` (§5.6).

### 5.5 Runtime y registro

- `async_setup_entry` (`__init__.py:24-40`) lee `entry.data["components"]`, o todos los opcionales si falta, y solo
  crea las entidades, energías y controles de esos componentes.
- Antes de cargar las plataformas, borra del registro de entidades las de la entry cuya clave pertenece a un
  componente no elegido, y del registro de dispositivos los dispositivos de componentes no elegidos.
- `enabled_keys` y `build_runtime` (`adapters/inbound/runtime.py`) reciben solo las claves de los componentes
  elegidos. Un tier sin entidades no tiene coordinator, como hoy.

### 5.6 Device ID

Distingue equipos del mismo tipo: dos inversores, cada uno con su batería, dan «Batería 0» y «Batería 1».

- Vale para cualquier marca y modelo. Es un dato de la entry: `entry.data["device_id"]`, entero ≥ 0.
- Único entre las entries cuyo perfil tiene el mismo `device_type` (`domain/profile.py:40`). El perfil de cada
  entry sale de `entry.data[CONF_PROFILE]`, como en reconfigure (`adapters/inbound/flow.py:159`). Dos
  inversores no comparten ID; un inversor y un sensor de irradiancia, sí.
- No cuentan las entries sin `device_id` ni las de un perfil que ya no existe.
- Valor por defecto: el menor entero ≥ 0 que no usa ninguna entry del mismo tipo. Con IDs 0 y 2, propone 1.
- Va en el nombre de todos los dispositivos de la entry, el principal y los de componente (§5.2). HA genera el
  `entity_id` desde el nombre del dispositivo y el de la entidad (`_attr_has_entity_name`,
  `adapters/inbound/entities/base.py:16`): `sensor.bateria_0_tension`.
- No tiene relación con el Unit ID de Modbus ni con el `device_id` del registro de dispositivos de HA.
- Entries creadas antes de v2: no se migran. Quedan sin ID y sus dispositivos se llaman sin número («Batería»)
  hasta que el usuario le pone uno en reconfigure (§4.1, §4.5).

### 5.7 Tier y activación de las extras

Hoy todas las extras van al tier `slow`, desactivadas y en diagnóstico (`profiles/ingeteam/oneplay_storage.py:74-94`).
Pasan al tier y la activación de la wiki del modelo
([registers-storage-1-play-tl-m.md](../../wiki/brands/ingeteam/storage-1-play-tl-m/registers-storage-1-play-tl-m.md),
«Tier y activación de las entidades de diagnóstico»). Resumen de sus reglas:

- Medidas eléctricas y alarmas: `fast`. Temperatura del inversor, ratio y motivos de limitación: `normal`.
  Contador de horas, aislamiento y consigna de reactiva: `slow`.
- Vatímetro interno, Cargas críticas y Cargador VE: activadas y sin categoría de diagnóstico. Bits del BMS:
  activados y en diagnóstico (§5.3). El resto: desactivadas y en diagnóstico.
- Las principales no cambian de tier, salvo las de red, que pasan a `instant` (§5.8).

Perfil: `_extra` gana `poll`, `enabled_default` y `entity_category` como parámetros, con los valores de hoy por
defecto. El `role` sigue en `DIAGNOSTIC`. La forma exacta se fija en el plan.

Bloques por tier con todos los componentes (`domain/blocks.py:17-31`, `max_gap` 9, 10 registros por bloque;
direcciones = registro − 30001). `min_tier_interval` cuenta todas las entidades del tier, activadas o no, a 1 s
por bloque (`application/poller.py:46-49`):

| Tier | Hoy | Con §5.3 y §5.7 | `min_tier_interval` |
|---|---|---|---|
| `fast` | 15-20, 33-37, 71-78 | 15-20, 28-37, 38-46, 48-54, 68-71, 78-80 | 3 s → 6 s |
| `normal` | 17-26, 31-35, 69-70 | 17-26, 29-35, 40-41, 57, 69-77 | 3 s → 5 s |
| `slow` | 6-7, 21-29, 38-46, 48-57, 59-60, 77-80 | 6-7, 21-27, 42, 59-60 | 6 s → 4 s |

- 6 s no cabe en el `fast` por defecto de hoy, 5 s (`const.py:10`): el paso de intervalos del alta (§3.6) daría
  `interval_too_short` con el valor propuesto. `DEFAULT_INTERVALS` pasa a `fast` 10 s en todos los perfiles.
  `normal` y `slow` no cambian.
- 30043 (42), de reason-labels, queda solo en `slow`: una petición más, ya contada.

Entries anteriores:

- Guardan sus intervalos en `entry.data[CONF_INTERVALS]` (`adapters/inbound/flow.py:147`): el STORAGE sigue con
  `fast` 5 s.
- El runtime solo lee las entidades activadas (`adapters/inbound/runtime.py:47-57`; ADR 0005). En una entry
  anterior son las principales y los 14 bits: 4 bloques en `fast`, que caben en 5 s.
- En reconfigure, el mínimo de `fast` es 6 s: con 5 s guardados, `reconfigure_intervals` da `interval_too_short`
  hasta que el usuario lo sube (§4.3).
- Las extras siguen desactivadas: el registro de entidades conserva `disabled_by`, y cambiar `enabled_default` no
  las activa. Sin migración.

Tests: `tests/unit/test_storage_profile.py:180-182` pasa a `fast` 6.0 y `normal` 5.0, y gana `slow` 4.0.
`tests/ha/test_config_flow.py:77` espera `fast` 10.

Documentación: `docs/decisions/0005-poll-tiers.md` (5, 60 y 3600 s), `docs/features/device-setup.md:90` y la wiki
del modelo (`:21`, «fast 5 s») pasan a 10 s.

La tabla no mueve aún la red. Con §5.8, 30070-30072 (69-71) salen de `fast` y `normal`: en `fast`, 68-71 queda en
68; en `normal`, 69-77 queda en 77. Ningún tier cambia su número de bloques.

### 5.8 Tier instantáneo

Objetivo: potencia, tensión y frecuencia de red más a menudo que el resto. Hoy van en `normal` (60 s) y `fast`
(5 s) (`profiles/ingeteam/oneplay_storage.py:178-188`).

**Límite del dispositivo.** Al menos 1 s entre peticiones y como mucho 10 registros por petición (`ABH2014IQM01`,
apdo. 19.6.1, pág. 50; `profiles/ingeteam/oneplay_storage.py:102-104`). El espaciado es de la conexión
(`adapters/outbound/modbus_gateway.py:38-39`) y lo comparten todos los tiers: un tier más rápido no acelera el
equipo, se reparte el mismo segundo.

**Tier.** `PollTier.INSTANT = "instant"` (`domain/types.py:27-30`), el primero del enum: el formulario de intervalos
recorre `PollTier` en orden (`adapters/inbound/flow.py:163`, `:180`, `:193`) y la instantánea sale arriba. El
runtime (`adapters/inbound/runtime.py:83`) y el diagnóstico (`adapters/inbound/diagnostics.py:21`) lo recorren
igual: no cambian. Etiqueta: «Instantánea» / «Instant».

**Entidades.** `grid_voltage` (30070), `grid_frequency` (30071) y `grid_power` (30072) pasan a `instant`
(`profiles/ingeteam/oneplay_storage.py:178`, `:180`, `:188`). Tres registros seguidos: un bloque, 1 s de mínimo.
`grid_import_energy` y `grid_export_energy` (`:232`, `:235`) siguen a su fuente: su tier es el de `grid_power`
(`adapters/inbound/runtime.py:70`; `domain/validate.py:60-72`). Su `max_gap_s` pasa a 15 s, 3 × intervalo
(`adapters/inbound/entities/energy.py:24`).

`ingeteam.oneplay` no tiene registros de red: no tiene tier `instant` ni sección en el formulario.

**Intervalo por defecto.** `DEFAULT_INTERVALS` (`const.py:10`) gana `"instant": 5`.

**Presupuesto.** Cada tier pide `min_tier_interval` peticiones por ciclo: bloques × 1 s
(`application/poller.py:46-49`). Validación nueva en el alta (§3.6) y en reconfigure (§4.3):

    Σ min_tier_interval(t) / intervalo(t) ≤ 1

Cuenta los tiers del formulario, con el perfil entero, como el mínimo. Si se pasa, error
`interval_budget_exceeded` con el total como placeholder: «Estos intervalos piden {rate} lecturas por segundo y el
dispositivo admite 1. Sube alguno.» Se comprueba después de `interval_too_short`. La función va en
`application/poller.py`, junto a `min_tier_interval`.

STORAGE con todos los componentes y los valores por defecto:

| Tier | Bloques | Intervalo | Peticiones/s |
|---|---|---|---|
| `instant` | 1 | 5 s | 0,20 |
| `fast` | 6 | 10 s | 0,60 |
| `normal` | 5 | 60 s | 0,08 |
| `slow` | 4 | 3600 s | 0,00 |
| Total | | | 0,88 |

Con `fast` 10 s y `normal` 60 s, `instant` admite 4 s (0,93); 3 s ya no (1,02).

**Sonda.** `probe_device` lee solo `fast` (`application/probe.py:17`). Pasa a leer `fast` e `instant`, para que el
paso de lecturas (§3.4) siga mostrando la red. Un bloque más: la sonda tarda 1 s más.

**Entries anteriores.**

- Sin la clave `instant` en `entry.data[CONF_INTERVALS]`: el runtime la completa con `DEFAULT_INTERVALS`
  (`adapters/inbound/runtime.py:68`). Sin migración.
- Un STORAGE anterior conserva `fast` 5 s y solo lee las activas (§5.7): 4 bloques en `fast`, 1 en `instant` y 2
  en `normal`. Son 4/5 + 1/5 + 2/60 ≈ 1,03 peticiones/s, algo por encima del límite. El espaciado encola las
  peticiones y los ciclos se retrasan un poco; no hay error. Al reconfigurar, el mínimo de `fast` ya exige 6 s
  (§4.3).

**Recorder.** A 5 s, las tres entidades de red dan unos 52 000 estados al día. Hoy, con `grid_power` a 5 s y las
otras dos a 60 s, unos 20 000.

**Tests.**

- `tests/unit/test_storage_profile.py:180`: `instant` 1.0.
- `tests/unit/test_poller.py`: presupuesto. Los valores por defecto pasan; `instant` 1 s con `fast` 10 s no.
- `tests/ha/test_config_flow.py:77` espera `instant` 5.
- `tests/ha/test_config_flow.py`: `interval_budget_exceeded` en el alta y en reconfigure.
- `tests/unit/test_translations.py`: la sección `instant` de los pasos de intervalos.

**Documentación.** ADR nuevo `docs/decisions/0016-instant-tier.md`, que amplía el 0005: el tier, el límite de una
petición por segundo y la validación de presupuesto. La wiki del modelo lleva 30070-30072 en `instant`.

## 6. Textos

- En `strings.json`, `translations/en.json` (copia literal, `tests/unit/test_translations.py:24-25`) y
  `translations/es.json` (mismas claves, `:28-29`).
- Pasos nuevos: `user` (marca), `model`, `components`, `readings`, `name` (con `serial_number` y `device_id`), `intervals`,
  `reconfigure_components`, `reconfigure_intervals`, `reconfigure_rename`. Errores nuevos: `invalid_serial_number`,
  `device_id_in_use`, `interval_budget_exceeded` (§5.8). Campo nuevo `device_id` en `name` y `reconfigure`. Sección
  nueva `instant` en `intervals` y `reconfigure_intervals`.
- Secciones nuevas: `selector.component`, `device` (cada clave con su par `_numbered`), `entity.binary_sensor`.
- Se quitan «entry», «host» y «endpoint» de los textos visibles. «Reconfigurar equipo» pasa a «Cambiar la
  conexión». `already_configured`: «Este dispositivo ya está añadido.». `reconfigure_successful`: «Cambios
  guardados.»
- Los textos del flujo dicen «dispositivo». Los nombres de componente («Inversor», «Batería») son datos del
  perfil, como el tipo de dispositivo del paso 2.
- Nombres de entidad: §5.4.

## 7. Piezas que cambian

| Pieza | Cambio |
|---|---|
| `adapters/inbound/flow.py` | Pasos `user`, `model`, `components`, `readings`, `name`, `intervals`; errores con placeholders; reconfigure en tres pasos (cuatro si cambia el Device ID) con sonda, Unit ID, componentes y lista de entidades; campo «Modelo» tras un error; Device ID en `name` y `reconfigure`; paso `reconfigure_rename` |
| `adapters/inbound/flow.py` · `format_readings` | Agrupación por componente, formato numérico y solo entidades `sensor` |
| `domain/types.py` | `Component`, `Platform.BINARY_SENSOR`, `Role.BMS_ALARM` y `Role.BMS_FLAG`, tipo de texto ASCII; `PollTier.INSTANT` (§5.8) |
| `domain/profile.py` | `component`, `bit`, `ComponentSpec`, `components`, `serial` |
| `domain/energy.py`, `domain/control.py` | `component` en `EnergySpec` y `GatedLimitSpec` |
| `domain/decode.py` | Bit a `bool`, texto ASCII |
| `domain/validate.py` | Componentes, bits y solape por bit, `serial` |
| `application/` | Selección de entidades por componentes; lectura opcional del número de serie y tier `instant` en la sonda (`probe.py`); validación de presupuesto (`poller.py`, §5.8) |
| `profiles/ingeteam/oneplay_storage.py` | `component` por entidad, `components`, 14 bits del BMS; tier y activación de las extras (§5.7); red en `instant` (§5.8) |
| `adapters/inbound/entities/base.py` | `DeviceInfo` por componente, `via_device`, `serial_number`; `translation_key` `_numbered` y `translation_placeholders` con Device ID |
| `adapters/inbound/entities/` | Plataforma `binary_sensor` |
| `adapters/inbound/runtime.py`, `__init__.py` | Componentes elegidos, limpieza del registro, `PLATFORMS` |
| `adapters/inbound/diagnostics.py` | Redacta `serial_number` |
| `const.py` | `CONF_SERIAL_NUMBER`, `CONF_COMPONENTS`, `CONF_DEVICE_ID`; `DEFAULT_INTERVALS` con `instant` 5 s y `fast` 10 s (§5.7, §5.8) |
| `manifest.json` | `integration_type: hub` |
| `strings.json`, `translations/` | §6 |
| `tests/ha/test_config_flow.py` | Pasos nuevos, menú, intervalos y componentes en el alta, campo «Modelo» tras un error, reconfigure en tres pasos, intervalos por tier, `instant` 5 s y `fast` 10 s por defecto, `interval_budget_exceeded`; Device ID (§12) |
| `tests/ha/` | Dispositivos por componente, `via_device`, limpieza del registro, `binary_sensor`; nombre de dispositivo y `entity_id` con Device ID (§12) |
| `tests/fakes.py` | Perfil falso con otro `device_type`, para la unicidad por tipo del Device ID |
| `tests/unit/test_storage_profile.py` | Bloques por tier (§5.7, §5.8), bits del BMS, tier y activación de las extras |
| `tests/unit/test_profiles.py` | `brand` = carpeta del perfil; reparto por componente |
| `tests/unit/test_readings.py` | Grupos por componente y formato; los `binary_sensor` no salen |
| `tests/unit/test_poller.py` | Validación de presupuesto (§5.8) |
| Tests de dominio (`decode`, `validate`) y de sonda | Bits, componentes, texto ASCII, `serial` opcional, fallo de lectura de serie |
| `docs/decisions/0005-poll-tiers.md`, `docs/features/device-setup.md`, wiki del modelo | `fast` 10 s por defecto (§5.7); red en `instant` (§5.8) |
| `docs/decisions/0016-instant-tier.md` | ADR nuevo: tier `instant` y presupuesto de una petición por segundo (§5.8) |
| `tests/unit/test_translations.py` | Etiqueta de modelo por perfil, nombre de cada componente y cada bit, par `_numbered` de cada dispositivo con `{device_id}`. El nombre de cada entidad se busca en la sección de su plataforma: hoy `:37` mira solo `entity.sensor` |

## 8. Datos y compatibilidad

- `VERSION` sigue en 2. `data` mantiene `host`, `port`, `unit_id`, `profile` e `intervals`, y gana
  `components`, `device_id` y `serial_number` opcional. `device_id` falta en las entries creadas antes de v2.
- Entry sin `components` (creadas antes): se toman todos los opcionales del perfil. Conserva las 47 entidades de
  hoy y no hace falta `async_migrate_entry`.
- `unique_id` de entry y de entidades no cambia: las entidades conservan su historial al pasar a otro dispositivo
  (`adapters/inbound/entities/base.py:30`).
- El dispositivo principal conserva su identificador. Su nombre pasa a «Inversor», salvo que el usuario lo
  renombrara en HA.
- Los `entity_id` ya creados no cambian (§5.4), salvo al cambiar el Device ID en reconfigure (§4.5).
- Entry sin `device_id`: sus dispositivos se llaman sin número. No hay `async_migrate_entry` (§5.6).
- Entry anterior: conserva sus intervalos guardados y sus extras desactivadas (§5.7). Gana los 14 bits del BMS,
  activados.

## 9. Criterios de aceptación

- El alta pide marca, modelo, IP, componentes, nombre, número de serie opcional, Device ID y, al final,
  frecuencia de lectura. Un número de serie escrito o leído aparece en la ficha del dispositivo principal.
- Cada modelo se ve con su descripción traducida. Un modelo sin componentes opcionales no muestra el paso.
- Ningún texto del flujo dice «inversor», «entry», «host» ni «endpoint», salvo los nombres de componente.
- Un dispositivo que no responde da un error con su IP, puerto y 20 s como máximo.
- Desde las lecturas se puede volver al modelo o a la conexión sin cerrar el flujo.
- Las lecturas salen agrupadas por componente elegido y con separador de miles.
- Tras el alta, la página de la integración muestra el título de la entry y debajo un dispositivo por componente
  elegido, con nombre corto. Los opcionales dicen «Conectado a través de Inversor».
- Un componente no elegido no tiene dispositivo ni entidades. Desmarcarlo en reconfigure los borra.
- «Batería» muestra los 14 bits del BMS como `binary_sensor`.
- Reconfigure cambia IP, puerto, Unit ID, número de serie, Device ID, componentes e intervalos. Si la sonda falla,
  no sigue ni guarda.
- Cada intervalo es una sección plegada con su mínimo y la lista de entidades del tier. Solo aparecen los tiers
  con entidades.
- Una entry creada antes conserva sus 47 entidades y su historial; gana los 14 bits del BMS, activados, y sus
  extras siguen desactivadas.
- Con los valores por defecto, el paso de intervalos del alta no da error en ningún perfil.
- En el STORAGE, tensión, frecuencia y potencia de red se actualizan cada 5 s por defecto. Unos intervalos que,
  juntos, pidan más de una lectura por segundo dan `interval_budget_exceeded`.
- Dos inversores del mismo modelo con Device ID 0 y 1 dan «Batería 0» y «Batería 1», y
  `sensor.bateria_0_tension` y `sensor.bateria_1_tension`, sin `_2`. Un ID ocupado por otro equipo del mismo
  tipo no deja avanzar.
- Cambiar el Device ID en reconfigure muestra cuántas entidades se renombran, se mantienen y chocan. Al
  confirmar, los `entity_id` generados cambian y el historial se conserva.
- Tests y lint en verde en CI.

## 10. Por decidir

Nada.

## 11. Pendiente de verificar en la VM

- Que HA rellena placeholders en el `data_description` de un campo dentro de una section (§4.3).
- Que una clave de `selector.profile.options` con punto se traduce (§3.2).
- Cómo se ve el menú `readings` con una descripción larga.
- Formato de miles en `es` y `en`.
- Que el nombre traducido del dispositivo (`translation_key` en `DeviceInfo`) sustituye al nombre guardado de un
  dispositivo ya creado.
- Cómo muestra la página de la integración una entry `hub` con varios dispositivos.
- Que `translation_placeholders` en `DeviceInfo` rellena el nombre del dispositivo, y que el registro de
  dispositivos guarda el nombre traducido (§5.2).
- Que el `entity_id` nuevo sale en el idioma de HA y con el Device ID: `sensor.bateria_0_tension` (§5.6).
- Cada cuánto actualiza el inversor 30070-30072 por dentro. Si es más lento que 5 s, `instant` lee valores
  repetidos (§5.8). El manual no lo dice.
- Qué vistas muestran el nombre completo del dispositivo con su ID y cuáles solo el de la entidad.
- Que el renombrado de §4.5 conserva el historial y que la recarga actualiza el nombre de los dispositivos.

## 12. Tests del Device ID

Se ejecutan en CI, como el resto.

`tests/ha/test_config_flow.py`, alta:

- `test_device_id_defaults_to_lowest_free`: sin entries propone 0; con inversores en 0 y 2 propone 1.
- `test_device_id_in_use_shows_error`: con un inversor en 0, enviar 0 da `device_id_in_use` y el paso no avanza.
- `test_device_id_free_across_device_types`: dos perfiles con distinto `device_type` usan el mismo ID. Perfil
  falso en `tests/fakes.py`: los dos de Ingeteam son `inverter`.
- `test_entries_without_device_id_do_not_block`: una entry sin `device_id` no ocupa ninguno.
- `test_add_inverter` (existe): además, `entry.data["device_id"]` se guarda.

`tests/ha/test_config_flow.py`, reconfigure:

- `test_reconfigure_prefills_device_id`: sale el ID guardado; en una entry sin ID sale vacío y es opcional.
- `test_reconfigure_device_id_excludes_own_entry`: dejar el mismo ID no da error.
- `test_reconfigure_same_id_skips_rename`: sin cambio de ID no aparece `reconfigure_rename`.
- `test_reconfigure_rename_renames_generated_ids`: de 0 a 2, `sensor.bateria_0_tension` pasa a
  `sensor.bateria_2_tension`; el `unique_id` no cambia.
- `test_reconfigure_rename_keeps_custom_ids`: un `entity_id` sin el prefijo no se toca.
- `test_reconfigure_rename_skips_collisions`: si el `entity_id` nuevo existe, el viejo se queda y sale en la lista.
- `test_reconfigure_rename_counts_in_placeholders`: los placeholders llevan renombradas, mantenidas y choques.

`tests/ha/`, dispositivos:

- Con ID, el dispositivo se llama «Batería 0» y una entidad nueva recibe `sensor.bateria_0_tension`.
- Sin ID, el dispositivo usa la clave sin placeholder: «Batería».
- Dos entries con ID 0 y 1 no generan ningún `_2`.

`tests/unit/test_translations.py`:

- Cada `device.<clave>` tiene su par `<clave>_numbered` con `{device_id}`, en `es` y `en`.
- Existen el error `device_id_in_use` y el paso `reconfigure_rename`.
