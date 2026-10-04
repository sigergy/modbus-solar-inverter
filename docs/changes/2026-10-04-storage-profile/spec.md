---
type: feature
area: profiles
layers: [domain, application, adapters, profiles]
status: done
date: 2026-10-04
---

# Spec 1 — Perfil INGECON SUN STORAGE 1Play TL M y energía calculada

## 1. Objetivo y alcance

El perfil `ingeteam.oneplay_storage` de la spec 0 lee registros de otro equipo. Su fuente,
`ACL2010IMB05`, es el mapa del INGECON SUN 1Play/3Play **sin storage**: holding `0x10xx`, FC03.
El equipo real del proyecto es un **INGECON SUN STORAGE 1Play TL M**. Su mapa es
`ABH2010IMB08`: input registers `30001-30081`, FC04
(`docs/wiki/brands/ingeteam/storage-1-play-tl-m/registers-storage-1-play-tl-m.md`).

Esta spec corrige el perfil y añade los contadores de energía que el mapa no trae.

**Dentro:**
- Perfil STORAGE con el id `ingeteam.oneplay_storage`. El mapa viejo pasa a `ingeteam.oneplay`.
- Entidades del núcleo, activas por defecto, y extra, deshabilitadas por defecto (§3).
- Cinco contadores de energía calculados por la integración (§4).
- Traducciones `en` y `es` de las entidades nuevas.

**Fuera:**
- Spec 2: escritura y control del vertido (CMD 26, dato `0x0A` «Grid power», `AAA0030IMB03`,
  págs. 19-20).
- Verificación de signos y escalas en equipo: se hace en la VM y se corrige en el perfil.
- Eventos y alarmas decodificados (`ABH2010IMC14`).

**Criterios de éxito:**
1. Un STORAGE 1Play TL M añadido con el perfil `ingeteam.oneplay_storage` muestra las
   entidades del núcleo con valor.
2. Los cinco contadores de energía crecen y sirven en el panel de Energía de HA: producción
   solar, red y batería.
3. Tras reiniciar HA, los contadores siguen desde el último total guardado.
4. Ninguna petición pide más de 10 registros, y hay al menos 1 s entre peticiones.

## 2. Contexto técnico verificado

- **Mapa:** `ABH2010IMB08` (rev. _I, 23/04/2025).
  - FC04, referencias 3xxxx. El registro 30001 es la dirección 0 (pág. 9).
  - Tabla de registros en las págs. 3-5; notas en las págs. 6-8.
  - **No trae ningún contador de energía.**
- **Comunicación:** `ABH2014IQM01`, apdo. 19.6.1, pág. 50. Un único cliente en el puerto 502,
  al menos 1 s entre peticiones y no más de 10 registros por petición.
- **Código existente que se reutiliza:**
  - `RegisterKind.INPUT` (`custom_components/modbus_solar/domain/types.py`).
  - El gateway ya lee input registers con `read_input_registers`
    (`adapters/outbound/modbus_gateway.py:30-33`).
  - `max_block_registers` ya limita el tamaño de bloque (`domain/profile.py`, `DeviceProfile`).
  - `enabled_keys` (`adapters/inbound/runtime.py:34-45`) decide qué se lee.
  - `read_tier` solo lee las entidades habilitadas del tier (`application/poller.py:28`).

## 3. Perfil STORAGE

### 3.1 Identidad y comunicación

| Campo | Valor |
|---|---|
| `id` | `ingeteam.oneplay_storage` |
| `models` | `("STORAGE 1Play TL M",)` |
| `min_request_interval_s` | `1.0` |
| `max_block_registers` | `10` |
| `max_gap` | `9` |
| `default_port` / `default_unit_id` | `502` / `1` |
| `probe_key` | `inverter_state` |

- `max_gap` es un campo nuevo de `DeviceProfile` (`int = 0`): huecos de hasta ese número de
  registros se leen dentro del mismo bloque. Lo usan `ModbusGateway` y `min_tier_interval`,
  que hoy reciben `max_gap` como argumento con valor 0.
  - Sin él, el tier `fast` del STORAGE necesita 6 peticiones: 6 s, más que los 5 s por
    defecto. El reconfigure daría `interval_too_short`.
  - Con `max_gap=9` y bloques de 10 registros, el tier `fast` son 3 peticiones
    (direcciones 15-20, 33-37 y 71-78) y el `normal` otras 3 (17-26, 31-35 y 69-70).
  - Leer huecos es seguro: «Within the Input Registers map it can be read whatever part of
    the memory» (`ABH2010IMB08`, pág. 9).
- Todas las entidades usan `RegisterKind.INPUT`.
- Dirección = registro − 30001. El perfil escribe el número de registro del PDF y un helper
  `_input(30016, …)` resta 30001, para que se pueda cotejar con el PDF.
- Fichero: `profiles/ingeteam/oneplay_storage.py`. El mapa viejo se mueve, sin cambios en sus
  registros, a `profiles/ingeteam/oneplay.py` con `id="ingeteam.oneplay"` y
  `models=("1Play TL M",)`. Los dos van en `ALL_PROFILES`.

### 3.2 Entidades del núcleo (activas)

Escalas tal como las da el PDF. `S16` = `INT16` del PDF.

| Clave | Registro | Tipo | Escala | Unidad | Tier | Clase |
|---|---|---|---|---|---|---|
| `inverter_state` | 30016 | U16 | 1 | — | fast | enum (Nota 2, §3.4) |
| `active_power` | 30038 | S16 | 1 | W | fast | power |
| `pv1_voltage` | 30032 | U16 | 1 | V | normal | voltage |
| `pv1_current` | 30033 | U16 | 0.01 | A | normal | current |
| `pv1_power` | 30034 | U16 | 1 | W | fast | power |
| `pv2_voltage` | 30035 | U16 | 1 | V | normal | voltage |
| `pv2_current` | 30036 | U16 | 0.01 | A | normal | current |
| `pv2_power` | 30037 | U16 | 1 | W | fast | power |
| `battery_voltage` | 30018 | U16 | 0.1 | V | normal | voltage |
| `battery_current` | 30019 | S16 | 0.01 | A | normal | current |
| `battery_power` | 30020 | S16 | 1 | W | fast | power |
| `battery_soc` | 30021 | U16 | 1 | % | fast | battery |
| `battery_soh` | 30022 | U16 | 1 | % | slow | — |
| `battery_state` | 30027 | U16 | 1 | — | normal | enum (Nota 3, §3.4) |
| `battery_temperature` | 30028 | S16 | 0.1 | °C | slow | temperature |
| `grid_voltage` | 30070 | U16 | 1 | V | normal | voltage |
| `grid_frequency` | 30071 | U16 | 0.1 | Hz | normal | frequency |
| `grid_power` | 30072 | S16 | 1 | W | fast | power |
| `load_power` | 30079 | U16 | 1 | W | fast | power |

- La red se lee del vatímetro externo (30070-30073): es el que mide el punto de conexión en
  la instalación del proyecto.
- Los sensores de potencia, tensión, corriente, frecuencia y temperatura llevan
  `state_class="measurement"`.
- `Role` gana un rol por magnitud del núcleo: `pv_voltage`, `pv_current`, `pv_power`,
  `battery_voltage`, `battery_current`, `battery_power`, `battery_soc`, `battery_soh`,
  `battery_state`, `battery_temperature`, `grid_voltage`, `grid_frequency`, `grid_power` y
  `load_power`. `inverter_state` y `active_power` siguen con `inverter_state` y `ac_power`.
  Los dos MPPT comparten rol.
- `battery_soh` va sin `device_class`: HA no tiene clase de salud de batería.

### 3.3 Entidades extra (deshabilitadas por defecto)

Todas con `enabled_default=False` y en el tier `slow`, salvo que se indique otra cosa.

| Clave | Registro | Tipo | Escala | Unidad |
|---|---|---|---|---|
| `operation_time` | 30007 | U32 | 1 | h |
| `battery_discharge_limit_reason` | 30030 | U16 | 1 | — (Nota 9, valor crudo) |
| `battery_charge_limit_reason` | 30078 | U16 | 1 | — (Nota 9, valor crudo) |
| `reactive_power` | 30039 | S16 | 1 | var |
| `power_factor` | 30040 | S16 | 0.001 | — (valor absoluto, Nota 6) |
| `power_reduction_ratio` | 30041 | U16 | 0.1 | % |
| `power_reduction_reason` | 30042 | U16 | 1 | — (Nota 7, valor crudo) |
| `critical_load_voltage` | 30044 | U16 | 1 | V |
| `critical_load_current` | 30045 | U16 | 0.01 | A |
| `critical_load_frequency` | 30046 | U16 | 0.01 | Hz |
| `critical_load_power` | 30047 | S16 | 1 | W |
| `internal_meter_voltage` | 30049 | U16 | 1 | V |
| `internal_meter_current` | 30050 | U16 | 0.01 | A |
| `internal_meter_frequency` | 30051 | U16 | 0.01 | Hz |
| `internal_meter_power` | 30052 | S16 | 1 | W |
| `dc_bus_voltage` | 30055 | U16 | 1 | V |
| `inverter_temperature` | 30058 | S16 | 0.1 | °C |
| `isolation_positive` | 30060 | U16 | 1 | kΩ |
| `isolation_negative` | 30061 | U16 | 1 | kΩ |
| `external_pv_power` | 30080 | U16 | 1 | W |
| `ev_charger_power` | 30081 | S16 | 1 | W |

- Los motivos de las Notas 7 y 9 se exponen como valor numérico crudo. Pasarlos a enum
  traducido queda fuera de esta spec.
- Las extra llevan `entity_category="diagnostic"` y el rol nuevo `Role.DIAGNOSTIC`
  (`diagnostic`).
- Llevan `device_class` y `state_class="measurement"` las que tienen magnitud física. Los
  motivos crudos y `power_factor` van sin `device_class`; `operation_time` va con
  `device_class="duration"` y `state_class="total_increasing"`.

### 3.4 Enumeraciones

`inverter_state` (30016, Nota 2, pág. 6):

| Valor | Opción |
|---|---|
| 0 | `stopped` |
| 1 | `starting` |
| 2 | `off_grid` |
| 3 | `on_grid` |
| 4 | `on_grid_battery_standby` |
| 5 | `waiting_to_connect` |
| 6 | `critical_loads_bypassed` |
| 7 | `emergency_charge_pv` |
| 8 | `emergency_charge_grid` |
| 9 | `locked_waiting_reset` |
| 10 | `error` |

`battery_state` (30027, Nota 3, pág. 6):

| Valor | Opción |
|---|---|
| 0 | `standby` |
| 1 | `discharging` |
| 2 | `charging_constant_current` |
| 3 | `charging_constant_voltage` |
| 4 | `floating` |
| 5 | `equalizing` |
| 6 | `bms_communication_error` |
| 7 | `not_configured` |
| 8 | `calibration_step_1` |
| 9 | `calibration_step_2` |
| 10 | `standby_manual` |

### 3.5 Signos (supuestos)

`ABH2010IMB08` no documenta el signo de `grid_power` (30072) ni de `battery_power` (30020).
Esta spec **asume**:

- `grid_power` > 0: importación de red; < 0: exportación.
- `battery_power` > 0: descarga; < 0: carga.

Se verifica en la VM con diagnostics. Si el equipo dice otra cosa, se invierte el filtro de
signo de los contadores afectados (§4.1) en el perfil.

### 3.6 Traducciones compartidas

`key` es también `translation_key` (`domain/profile.py:21`). `inverter_state` existe en los
dos perfiles con opciones distintas. Su bloque `state` de `strings.json` lleva la unión de las
opciones de ambos perfiles. `test_translations.py` comprueba que el bloque `state` de cada
clave es exactamente la unión de los `enum` de todos los perfiles con esa clave.

## 4. Energía calculada

### 4.1 Contadores

| Clave | Fuentes | Filtro | Rol |
|---|---|---|---|
| `solar_energy` | `pv1_power`, `pv2_power` | potencia > 0 | `ENERGY_SOLAR` |
| `grid_import_energy` | `grid_power` | potencia > 0 | `ENERGY_GRID_IMPORT` |
| `grid_export_energy` | `grid_power` | potencia < 0, en valor absoluto | `ENERGY_GRID_EXPORT` |
| `battery_charge_energy` | `battery_power` | potencia < 0, en valor absoluto | `ENERGY_BATTERY_CHARGE` |
| `battery_discharge_energy` | `battery_power` | potencia > 0 | `ENERGY_BATTERY_DISCHARGE` |

- Sensores `device_class="energy"`, `state_class="total_increasing"`, en kWh, activos por
  defecto.
- La potencia de cada muestra es la suma de sus fuentes; después se aplica el filtro.
- `solar_energy` integra la potencia DC de los MPPT, antes de las pérdidas del inversor. La
  potencia AC (30038) incluye la descarga de la batería y no sirve para producción solar.

### 4.2 Modelo

- **`domain/energy.py`** (puro, sin HA):
  - `SignFilter` (`POSITIVE`, `NEGATIVE`).
  - `EnergySpec` (frozen): `key`, `role`, `sources: tuple[str, ...]`, `sign: SignFilter`,
    `enabled_default: bool = True`.
  - `EnergyAccumulator`: recibe muestras `(t: float, power_w: float | None)` y acumula kWh por
    la regla del trapecio sobre la potencia ya filtrada.
    - Una muestra `None` (fuente sin valor o con error) corta la serie: el tramo que la
      contiene no se integra.
    - Un tramo de más de `max_gap_s` segundos no se integra.
    - El total nunca baja. Se puede inicializar con un total restaurado.
- **`DeviceProfile`** gana `energies: tuple[EnergySpec, ...] = ()`.
- **`domain/validate.py`** añade comprobaciones:
  - clave de energía duplicada o repetida con una entidad;
  - fuente inexistente;
  - fuentes en tiers distintos;
  - fuente que no es de potencia (`device_class != "power"`).
- **`Role`** gana los cinco roles de la tabla.

### 4.3 Entidad de HA

- `adapters/inbound/entities/energy.py`: `ModbusSolarEnergySensor(ModbusSolarEntity,
  RestoreSensor)`.
  - Se suscribe al coordinador del tier de sus fuentes.
  - En cada actualización correcta toma `t` de `dt_util.utcnow()` y la suma de sus fuentes.
  - Un fallo de lectura (`last_update_success` falso) corta la serie.
  - `max_gap_s = 3 × intervalo del tier`.
  - El `TierCoordinator` de un tier con fuentes de energía usa `always_update=True`.
    Con `always_update=False`, HA no avisa a las entidades si el `TierResult` no cambia
    (`homeassistant/helpers/update_coordinator.py:590-598`, HA 2026.9.4). Una potencia
    constante dejaría de generar muestras y se perdería energía por `max_gap_s`.
    `TierCoordinator` gana el parámetro `always_update: bool`; `build_runtime` lo calcula.
  - Al añadirse a HA toma una primera muestra si el coordinador ya tiene datos.
  - Precisión de presentación sugerida: 3 decimales.
  - Al arrancar, restaura el último `native_value` con `async_get_last_sensor_data()`. Lo que
    pasa con HA apagado no se integra.
- `build_sensors` (`adapters/inbound/entities/factory.py`) crea también estos sensores a
  partir de `profile.energies`.

### 4.4 Qué se lee

`enabled_keys` (`adapters/inbound/runtime.py:34-45`) añade las fuentes de cada energía
habilitada, aunque su sensor de potencia esté deshabilitado. El estado habilitado de una
energía se consulta en el entity registry igual que el de una entidad.

## 5. Migración

- El id `ingeteam.oneplay_storage` no cambia: los equipos ya configurados pasan al mapa nuevo
  sin migrar la subentry.
- `inverter_state` y `active_power` conservan su clave y su `unique_id`. Sus opciones de enum
  y su registro cambian.
- `total_energy` desaparece del perfil. Su entidad queda huérfana en el registry y HA la
  muestra como «ya no la proporciona la integración». Se borra a mano desde la UI. El
  histórico de estadísticas no se migra a `solar_energy`.

## 6. Tests

Solo en CI (ADR 0007).

- **Unitarios:**
  - `EnergyAccumulator`: trapecio, filtro de signo, huecos por `None` y por `max_gap_s`, total
    restaurado y total que nunca baja.
  - `validate_profile` con energías: cada comprobación nueva de §4.2.
  - Perfil STORAGE:
    - válido;
    - todas las entidades `INPUT`;
    - `max_block_registers == 10`;
    - direcciones de muestra contra el PDF (`inverter_state` → 15, `grid_power` → 71);
    - ningún bloque planificado con más de 10 registros.
  - Perfil `ingeteam.oneplay`: los mismos tres registros que hoy.
- **HA:**
  - las entidades del núcleo existen y las extra están deshabilitadas;
  - un contador de energía crece entre dos lecturas;
  - un fallo de lectura no suma energía;
  - se restaura tras recargar la entry;
  - las fuentes se leen con el sensor de potencia deshabilitado.

## 7. Documentación

- `docs/features/monitoring.md`: entidades, energía, signos supuestos y panel de Energía.
- `docs/guides/setup.md`: límites de `ABH2014IQM01` y entidad huérfana `total_energy`.
- `docs/architecture/`: `EnergySpec`, acumulador y entidad de energía.
- ADR nuevo: «Energía calculada por la integración cuando el equipo no la da».

## 8. Riesgos y pendientes

- Signos de red y batería supuestos (§3.5).
- Escalas sin verificar en equipo, sobre todo `[A x100]`, `[Hz x10]` frente a `[Hz x100]` y
  `[V x 10]`.
- U16 para `pv1_power`, `pv2_power` y `load_power` limita a 65 535 W. Sobra para un equipo de
  3-6 kW.
- La precisión de la energía depende del intervalo del tier `fast`, que nunca baja de 1 s por
  petición. Con unas 5 peticiones por ciclo, el muestreo real ronda los 5 s.
- Con otro cliente Modbus conectado (p. ej. un EMS), Ingeteam no garantiza las respuestas
  (`ABH2014IQM01`, pág. 50).
