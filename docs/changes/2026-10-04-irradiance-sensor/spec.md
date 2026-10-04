---
type: feature
area: profiles
layers: [domain, profiles, adapters]
status: done
date: 2026-10-04
---

# Spec 4 — Perfil del sensor de irradiancia Si-RS485TC-…-MB

> Es la «Spec 3: otros equipos (célula de irradiancia, meters)» que anotó
> `docs/changes/2026-10-04-skeleton/spec.md:32`. El número 3 ya lo usa el control del vertido
> (`docs/changes/2026-10-04-export-control/spec.md`), por eso esta es la 4.

## 1. Objetivo y alcance

Hasta ahora todos los perfiles son inversores Ingeteam (`profiles/__init__.py:7`). Esta spec añade el
primer equipo de otra marca y de otro tipo: el sensor de irradiancia de silicio de Ingenieurbüro
Mencke & Tegtmeyer, serie Si-RS485TC-…-MB. El sensor habla Modbus RTU por RS485. Se instala detrás de
una pasarela RS485 → Modbus TCP, así que para la integración es un equipo TCP más: no hace falta
ningún transporte nuevo.

**Dentro:**
- Marca `mencke_tegtmeyer` y perfil `mencke_tegtmeyer.si_rs485`, un solo perfil para los cuatro
  modelos de la serie (§3).
- Cuatro sensores: irradiancia, velocidad del viento, temperatura de la célula y temperatura
  externa (§3.2).
- Cuatro roles nuevos en `Role` (§3.3).
- Textos del alta sin la palabra «inversor» (§4) y traducciones de las cuatro entidades.
- Los dos PDF del fabricante y la tabla de registros en `docs/wiki/brands/mencke-tegtmeyer/` (§6).

**Fuera:**
- Producción estimada a partir de la irradiancia.
- FC 0x46: número de serie, versión de firmware y parámetros de comunicación (`Specification` págs.
  3-5). Sin él, el perfil no distingue el modelo (§2.3).
- Registro 0009, temperatura externa 2 (solo firmware ≥ 2.01, `Specification` pág. 1).
- Los registros de compatibilidad 0001, 0002, 0005 y 0006 (`Specification` pág. 2): el perfil usa los
  nuevos, que cubren el rango completo de -40…+90 °C.
- Escritura: el sensor no tiene registros escribibles.
- Perfiles Ingeteam: no cambian.

**Criterios de éxito:**
1. El selector del alta ofrece «Ingenieurbüro Mencke & Tegtmeyer · Si-RS485TC-T-MB, …».
2. Con el sensor detrás de la pasarela, la entry se crea y muestra las cuatro lecturas en la
   confirmación.
3. Las cuatro entidades salen con la clase, la unidad y la `state_class` que HA espera para
   irradiancia, viento y temperatura.
4. Un ciclo `fast` es una sola petición FC04 de 9 registros, y el intervalo por defecto de 5 s la
   admite (`DEFAULT_INTERVALS`, `const.py:10`).
5. Una temperatura negativa se muestra con su signo: el raw `0xFFCE` es -5,0 °C.
6. Los perfiles Ingeteam y sus tests no cambian de comportamiento.

## 2. Contexto técnico verificado

### 2.1 Protocolo y registros (`Specification_Si-RS485_MODBUS.pdf`, feb 2022, firmware 2.01)

- Modbus RTU. Funciones soportadas: 0x03 (Read Holding Register) y 0x04 (Read Input Register)
  (pág. 1). Valores de fábrica: 9600 baudios, 8N1, dirección 1 (pág. 1). Empieza a atender Modbus 4 s
  después del encendido (pág. 1).
- Registros nuevos (pág. 1):

| Registro | Valor | Ganancia | Offset | Rango físico | Tipo | Nota |
|---|---|---|---|---|---|---|
| 0000 | Irradiancia, W/m² | 0,1 | 0 | 0…1500 W/m² | UINT16 | hasta firmware 1.52 el rango es 0…1400 |
| 0003 | Velocidad del viento, m/s | 0,1 | 0 | 0…80 m/s | UINT16 | opcional |
| 0007 | Temperatura de la célula, °C | 0,1 | 0 | -40…+90 °C | INT16 | solo firmware ≥ 1.53 |
| 0008 | Temperatura externa 1, °C | 0,1 | 0 | -40…+90 °C | INT16 | solo firmware ≥ 1.53; opcional |
| 0009 | Temperatura externa 2, °C | 0,1 | 0 | -40…+90 °C | INT16 | solo firmware ≥ 2.01; no se usa |

- «Los registros 0003, 0008 y 0009 son opcionales en algunos tipos de sensor. Si el sensor no soporta
  el registro, devuelve el valor 0» (pág. 1). **No devuelve error.**
- Los registros 0001, 0002, 0004, 0005 y 0006 existen (pág. 2): 0001, 0002, 0005 y 0006 son
  compatibilidad con firmwares viejos y 0004 está «reserved» con valor 0. Leerlos no da error.

### 2.2 Registros activos por modelo (pág. 5)

| Serie de serie | Modelo | Registros activos |
|---|---|---|
| `485-1` | Si-RS485TC-T-MB | 0000, 0007 |
| `485-2` | Si-RS485TC-2T-MB | 0000, 0007, 0008 |
| `485-3` | Si-RS485TC-2T-v-MB | 0000, 0003, 0007, 0008 |
| `485-4` | Si-RS485TC-T-Tm-MB | 0000, 0007, 0008 |

El significado del registro 0008 depende del modelo (`Si_Instruction_digital_2017_E_SP.pdf`, pág. 1):
en el `-2T` es un sensor de temperatura ambiente externo cableado; en el `-T-Tm`, un sensor de
temperatura del módulo cableado. En el `-2T-v` hay conectores hembra para un sensor de temperatura
externo opcional y un sensor de viento opcional: sin ellos conectados, los registros devuelven 0 o un
valor sin sentido (la guía no dice cuál).

### 2.3 Qué no se puede saber desde el perfil

- El modelo y el firmware solo se leen con FC 0x46, subfunciones 07 y 08 (págs. 4-5). `DeviceGateway`
  solo lee registros (`ports/device.py:10-13`) y esta spec no añade esa función. Consecuencia: el perfil
  no puede ocultar las entidades que el modelo no tiene (§7, riesgo 1).
- Un registro opcional ausente y una lectura real de 0 son indistinguibles (pág. 1).

### 2.4 Código existente que se reutiliza

- `DeviceProfile`, `EntitySpec` y `RegisterSpec` (`domain/profile.py:12-50`): el perfil nuevo es un
  literal más, como `ONEPLAY` (`profiles/ingeteam/oneplay.py:6-51`). No se toca `domain/profile.py`.
- `RegisterKind.INPUT` y `DataType.S16`/`U16` (`domain/types.py:6-24`).
- `max_gap` ya agrupa huecos dentro de un bloque (`domain/blocks.py:17-31`,
  `adapters/outbound/modbus_gateway.py:36-37`, `application/poller.py:46-49`).
- `decode` ya pasa S16 a negativo y redondea el ruido de la escala (`domain/decode.py:19-34`).
- `validate_profile` comprueba claves duplicadas, `probe_key` y solapes (`domain/validate.py:48-96`).
- `Catalog` agrupa por marca y ordena (`application/catalog.py:16-20`); el flujo lo usa tal cual
  (`adapters/inbound/flow.py:88-92`).
- `BRAND_TITLES` da el título de marca al selector, al nombre por defecto y al `manufacturer` del
  dispositivo (`const.py:12`, `adapters/inbound/flow.py:89`, `:150`, `entities/base.py:39`).
- La plataforma `sensor` ya lee `device_class`, `unit` y `state_class` del `EntitySpec`: no hay
  plataforma nueva.

## 3. Perfil `mencke_tegtmeyer.si_rs485`

### 3.1 Identidad y comunicación

Fichero: `profiles/mencke_tegtmeyer/si_rs485.py` (más su `__init__.py`, como `profiles/ingeteam/`).

| Campo | Valor |
|---|---|
| `id` | `mencke_tegtmeyer.si_rs485` |
| `brand` | `mencke_tegtmeyer` |
| `device_type` | `irradiance_sensor` |
| `models` | `("Si-RS485TC-T-MB", "Si-RS485TC-2T-MB", "Si-RS485TC-2T-v-MB", "Si-RS485TC-T-Tm-MB")` |
| `min_request_interval_s` | `1.0` |
| `max_block_registers` | `125` (valor por defecto, límite de FC03/FC04) |
| `max_gap` | `3` |
| `default_port` / `default_unit_id` | `502` / `1` |
| `probe_key` | `irradiance` |

- `min_request_interval_s=1.0`: el PDF no fija un mínimo entre peticiones. Se usa el mismo valor que en
  Ingeteam (`profiles/ingeteam/oneplay.py:12`) y se anota como supuesto. La pasarela y el bus RS485
  limitan en la práctica, no el sensor.
- `max_gap=3`: las entidades están en 0, 3, 7 y 8. Los huecos son 1-2 (2 registros), 4-6 (3 registros)
  y ninguno entre 7 y 8. Con `max_gap=3`, `plan_blocks` fusiona todo en **un** bloque `INPUT`, dirección
  0, 9 registros. Con menos de 3 serían dos o más peticiones. Leer los huecos es seguro: existen
  (§2.1) y no dan error.
- `default_unit_id=1` y el puerto 502 son los valores de fábrica del sensor (§2.1) y los habituales de
  una pasarela. La dirección del esclavo RS485 la configura el sensor (`Specification` pág. 3, FC 0x46
  subfunción 04); la pasarela debe respetar 9600 8N1 si no se ha cambiado.
- Un solo perfil para toda la serie: los cuatro modelos comparten la misma tabla de registros (§2.2) y
  solo difieren en cuáles responden con datos reales.

### 3.2 Entidades

Todas con `platform=Platform.SENSOR`, `RegisterKind.INPUT` (FC04), `PollTier.FAST`,
`enabled_default=True`, `state_class="measurement"` y sin `entity_category`.

| Clave | Rol | Registro | Tipo | Escala | `device_class` | Unidad |
|---|---|---|---|---|---|---|
| `irradiance` | `IRRADIANCE` | 0 | U16 | 0,1 | `irradiance` | `W/m²` |
| `wind_speed` | `WIND_SPEED` | 3 | U16 | 0,1 | `wind_speed` | `m/s` |
| `cell_temperature` | `CELL_TEMPERATURE` | 7 | S16 | 0,1 | `temperature` | `°C` |
| `external_temperature` | `EXTERNAL_TEMPERATURE` | 8 | S16 | 0,1 | `temperature` | `°C` |

- `external_temperature` se llama «external» y no «ambient» porque, según el modelo, mide la
  temperatura ambiente o la del módulo (§2.2).
- Tier `fast` para todas: una sola petición sirve a las cuatro y el equipo es local, así que no hay
  motivo para separar tiers. Intervalo mínimo del tier: 1 bloque × 1,0 s = 1,0 s
  (`application/poller.py:46-49`), menor que los 5 s por defecto.
- Sin `offset`: los registros nuevos 0007 y 0008 ya traen el valor con offset 0 (pág. 1). Los viejos
  0001, 0002, 0005 y 0006 usan offsets y están fuera (§1).
- `device_class` y `unit` van como cadenas, porque `domain` no importa HA (`domain/profile.py:28`).
  Los valores `irradiance`, `wind_speed` y `temperature` son los de `SensorDeviceClass` en HA; se
  comprueban en los tests de HA, no con una dependencia en `domain`.
- La irradiancia nocturna es 0, un valor válido: `probe_key` decodifica sin problema (`application/probe.py:10-17`).

### 3.3 Roles nuevos (`domain/types.py:33-60`)

`Role` gana `IRRADIANCE = "irradiance"`, `WIND_SPEED = "wind_speed"`,
`CELL_TEMPERATURE = "cell_temperature"` y `EXTERNAL_TEMPERATURE = "external_temperature"`. Sus valores
se guardan en config y diagnostics: no se cambian después (`domain/types.py:1`). Son roles semánticos
independientes de la marca, para el frontend futuro (`docs/research/architecture-analysis.md:150`).

### 3.4 Catálogo

`ALL_PROFILES` pasa a `(ONEPLAY, ONEPLAY_STORAGE, SI_RS485)` (`profiles/__init__.py:7`).
`Catalog.brands()` devuelve `["ingeteam", "mencke_tegtmeyer"]`: el selector lista primero Ingeteam,
después la marca nueva (`application/catalog.py:16-20`).

## 4. Marca, flujo de alta y traducciones

### 4.1 Marca

`BRAND_TITLES` (`const.py:12`) gana `"mencke_tegtmeyer": "Ingenieurbüro Mencke & Tegtmeyer"`. El
selector muestra `«Ingenieurbüro Mencke & Tegtmeyer · Si-RS485TC-T-MB, Si-RS485TC-2T-MB, …»`
(`flow.py:89`). El nombre por defecto de la entry es
`«Ingenieurbüro Mencke & Tegtmeyer Si-RS485TC-T-MB»` (`flow.py:150`): se corrige al nombrar el equipo.

### 4.2 Textos del alta

Los textos del flujo dicen «inversor» (`strings.json:6`, `:12-13`, `:28-29`). Con un sensor son
incorrectos. Pasan a «device» / «equipo». No se tocan los nombres de entidad (`inverter_state`,
`inverter_temperature`, etc.) ni `exceptions.write_failed` (`strings.json:239`): el sensor no tiene
controles, así que ese mensaje no se emite para él.

| Clave | `en` (`strings.json`, `translations/en.json`) | `es` (`translations/es.json`) |
|---|---|---|
| `config.step.user.description` | `Each device is a separate entry. Add one entry per device.` | `Cada equipo es una entry independiente. Añade una entry por equipo.` |
| `config.step.connection.title` | `Connect to the device` | `Conectar con el equipo` |
| `config.step.connection.description` | `Enter the IP address or hostname of the device. The connection is tested before going on.` | `Escribe la dirección IP o el nombre de host del equipo. La conexión se prueba antes de seguir.` |
| `config.step.confirm.title` | `Device found` | `Equipo encontrado` |
| `config.step.confirm.description` | `The device at {host} answered:\n\n{readings}` | `El equipo en {host} ha respondido:\n\n{readings}` |

### 4.3 Entidades nuevas

`entity.sensor` gana cuatro claves:

| Clave | `en` | `es` |
|---|---|---|
| `irradiance` | Irradiance | Irradiancia |
| `wind_speed` | Wind speed | Velocidad del viento |
| `cell_temperature` | Cell temperature | Temperatura de la célula |
| `external_temperature` | External temperature | Temperatura externa |

`translations/en.json` sigue siendo copia literal de `strings.json`
(`tests/unit/test_translations.py:24-25`).

## 5. Tests

Solo en CI (ADR 0007). Los helpers existentes se reutilizan; no se crea ninguno nuevo (§8).

- **Unitarios, `tests/unit/test_si_rs485_profile.py` (nuevo, junto a `test_storage_profile.py`):**
  - identidad: id, marca, tipo, modelos, puerto, unidad, `probe_key`, `min_request_interval_s`,
    `max_gap`, `validate_profile == []`;
  - las cuatro entidades: dirección, tipo, escala, clase, unidad, `state_class`, tier, rol,
    `RegisterKind.INPUT`, `enabled_default`;
  - `plan_blocks` con los registros del perfil devuelve un solo `Block(INPUT, 0, 9)`;
  - `min_tier_interval(SI_RS485, FAST) == 1.0`;
  - `decode` del raw `0xFFCE` en el registro 7 da `-5.0`; el raw `1234` en el registro 0 da `123.4`.
- **`tests/unit/test_profiles.py`:** `test_catalog_lookup` pasa a esperar las dos marcas, el perfil nuevo
  y `CATALOG.get("mencke_tegtmeyer.si_rs485")`. `test_all_profiles_are_valid` ya recorre `ALL_PROFILES`.
- **`tests/unit/test_translations.py`:** sin cambios. Su test de entidades ya recorre `ALL_PROFILES`
  (`test_translations.py:32-44`) y falla mientras falten las cuatro claves.
- **HA, `tests/ha/test_config_flow.py`:** `test_model_step_lists_every_profile` espera la opción
  `{"value": "mencke_tegtmeyer.si_rs485", "label": "Ingenieurbüro Mencke & Tegtmeyer · Si-RS485TC-T-MB,
  Si-RS485TC-2T-MB, Si-RS485TC-2T-v-MB, Si-RS485TC-T-Tm-MB"}` después de las de Ingeteam.
- **Sin test propio:** el comportamiento con la pasarela real, el firmware < 1.53 y los modelos sin
  registro opcional. Se comprueban en la VM.

## 6. Documentación

- `docs/wiki/brands/mencke-tegtmeyer/README.md`: procedencia, revisión y SHA-256 de los dos PDF
  (ADR 0006).
- `docs/wiki/brands/mencke-tegtmeyer/si-rs485-mb/`: los dos PDF y `registers.md` con citas de página.
  Indica que los registros 7 y 8 exigen firmware ≥ 1.53.
- `docs/features/monitoring.md`: sección del sensor de irradiancia.
- `docs/architecture/domain.md`: fila de `Role` con los cuatro roles nuevos.
- `docs/README.md`: fila de este cambio. `README.md`: fila de equipos soportados y paso 3 de la
  configuración («del equipo»).
- ADR 0013 «Un perfil por serie de sensores con registros opcionales» (`docs/decisions/`): recoge la
  decisión de §3.1 y su coste (§7, riesgo 1).

## 7. Riesgos y pendientes

1. **Entidades sin sentido en algunos modelos.** Las cuatro entidades están activas en todos los
   modelos (decisión de producto). El `-T` no tiene los registros 0003 ni 0008, y el `-2T`, `-T-Tm`
   no tienen el 0003: ahí devuelven 0 (§2.1) y HA mostrará 0 m/s o 0 °C como si fueran medidas. El
   `-2T-v` sin sensores externos conectados puede dar lo mismo. Mitigación manual: deshabilitar la
   entidad desde la UI de HA. Si molesta, la salida es leer el número de serie por FC 0x46 y filtrar
   entidades por modelo, o un perfil por modelo; ninguna está en esta spec.
2. **Firmware < 1.53.** Los registros 0007 y 0008 no existen (§2.1): según el PDF, el resultado de
   leerlos en esos firmwares no está documentado. Fuera de alcance; un sensor de ese firmware tendría
   que usar los registros de compatibilidad.
3. **Escalas sin verificar en equipo.** Se toman del PDF (ganancia 0,1). Se comprueban en la VM con
   diagnostics (`raw` frente a `value`), como en los perfiles Ingeteam.
4. **Espaciado entre peticiones.** `min_request_interval_s=1.0` es un supuesto (§3.1). Si la pasarela
   o el bus lo necesitan, se ajusta en el perfil.
5. **Arranque del sensor.** Tarda 4 s en atender Modbus tras el encendido (pág. 1). Un equipo recién
   alimentado puede fallar en el alta con `cannot_connect`; se reintenta.
6. **Rango de irradiancia en firmware viejo.** Hasta 1.52 el máximo es 1400 W/m² (pág. 1). No afecta
   al perfil: no declara máximo.
7. **Procedencia de los PDF.** ADR 0006 pide documentación oficial y pública. Los PDF son del
   fabricante (pie de página: www.ib-mut.de), pero la URL de descarga no está registrada. Pendiente
   de anotar.
8. **Comunicación del bus.** La guía da 38400 baudios como máximo (`Si_Instruction_digital_2017_E_SP.pdf`,
   pág. 4); la especificación lista también 57600 sin que la tabla de FC 0x46 lo admita
   (`Specification` págs. 1 y 4). No afecta a la integración (la velocidad es de la pasarela) y se
   documenta en `registers.md`.

## 8. Reutilizar, corregir o crear

Decisión de cada pieza (skill `leer-reutilizar-corregir`):

| Pieza | Desenlace | Motivo |
|---|---|---|
| Modelo `DeviceProfile`/`EntitySpec` | reutilizar | mismo contrato: registros → entidades (`domain/profile.py:12-50`) |
| `max_gap`, `plan_blocks`, `decode` | reutilizar | ya resuelven el hueco y el signo (§2.4) |
| `profiles/mencke_tegtmeyer/si_rs485.py` | crear | otro equipo y otra tabla de registros; el literal no se comparte con `oneplay.py` |
| `tests/unit/test_si_rs485_profile.py` | crear | un fichero de tests por perfil, como `test_storage_profile.py` |
| Tests de catálogo y selector | corregir | ya existen y asumen una sola marca (`test_profiles.py:67-71`, `test_config_flow.py:47-50`) |
| Textos «inverter» del flujo | corregir | misma clave, texto que ya no vale para todos los equipos |
