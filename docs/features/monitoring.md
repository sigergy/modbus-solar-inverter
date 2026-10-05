# Funcionalidad: monitorización

Documento vivo. Rutas bajo `custom_components/modbus_solar/` salvo indicación. Nombres de las entidades en `strings.json:262-487`.

## Perfiles

| Perfil | Equipo | Mapa | Fichero |
|---|---|---|---|
| `ingeteam.oneplay_storage` | INGECON SUN STORAGE 1Play TL M | `ABH2010IMB08`: input registers 30001-30081, FC04 ([registers-storage-1-play-tl-m.md](../wiki/brands/ingeteam/storage-1-play-tl-m/registers-storage-1-play-tl-m.md)) | `profiles/ingeteam/oneplay_storage.py` |
| `ingeteam.oneplay` | INGECON SUN 1Play TL M, sin storage | `ACL2010IMB05`: holding `0x10xx`, FC03 ([registers.md](../wiki/brands/ingeteam/1-play-tl-m/registers.md)) | `profiles/ingeteam/oneplay.py` |
| `mencke_tegtmeyer.si_rs485` | Sensor de irradiancia Si-RS485TC-…-MB (cuatro modelos) | `Specification_Si-RS485_MODBUS`: input registers 0, 3, 7 y 8, FC04 ([registers.md](../wiki/brands/mencke-tegtmeyer/si-rs485-mb/registers.md)) | `profiles/mencke_tegtmeyer/si_rs485.py` |

Los tres van en el catálogo (`profiles/__init__.py:8`).

## Tiers y componentes

Cada entidad lee en uno de cuatro tiers: `instant` (5 s por defecto), `fast` (10 s), `normal` (60 s) y `slow` (3600 s) (`const.py:13`). Los intervalos se eligen en el alta y en el reconfigure, con un mínimo por tier y un presupuesto de una petición por segundo entre todos: ver [device-setup](device-setup.md) y ADR [0016](../decisions/0016-instant-tier.md).

El STORAGE reparte sus entidades en componentes, cada uno con su dispositivo en HA: el inversor (principal), `pv`, `battery`, `grid`, `internal_meter`, `critical_loads`, `load` y `ev_charger` (`profiles/ingeteam/oneplay_storage.py:39-69`, `:164-172`). Solo se crean las entidades de los componentes elegidos en el alta. ADR [0015](../decisions/0015-device-per-component.md).

## Sensores del STORAGE 1Play TL M

Todos son input registers. Dirección = registro − 30001 (`profiles/ingeteam/oneplay_storage.py:72-74`).

### Núcleo (activos)

Definidos en `profiles/ingeteam/oneplay_storage.py:174-253`. Potencia, tensión, corriente, frecuencia y temperatura llevan `state_class=measurement`.

| Clave | Registro | Tipo | Escala | Unidad | Tier |
|---|---|---|---|---|---|
| `inverter_state` | 30016 | U16 | 1 | — (enum) | `fast` |
| `active_power` | 30038 | S16 | 1 | W | `fast` |
| `pv1_voltage` / `pv2_voltage` | 30032 / 30035 | U16 | 1 | V | `normal` |
| `pv1_current` / `pv2_current` | 30033 / 30036 | U16 | 0,01 | A | `normal` |
| `pv1_power` / `pv2_power` | 30034 / 30037 | U16 | 1 | W | `fast` |
| `battery_voltage` | 30018 | U16 | 0,1 | V | `normal` |
| `battery_current` | 30019 | S16 | 0,01 | A | `normal` |
| `battery_power` | 30020 | S16 | 1 | W | `fast` |
| `battery_soc` | 30021 | U16 | 1 | % | `fast` |
| `battery_soh` | 30022 | U16 | 1 | % | `slow` |
| `battery_state` | 30027 | U16 | 1 | — (enum) | `normal` |
| `battery_temperature` | 30028 | S16 | 0,1 | °C | `slow` |
| `grid_voltage` | 30070 | U16 | 1 | V | `instant` |
| `grid_frequency` | 30071 | U16 | 0,1 | Hz | `instant` |
| `grid_power` | 30072 | S16 | 1 | W | `instant` |
| `load_power` | 30079 | U16 | 1 | W | `fast` |

La red se lee del vatímetro externo (30070-30073) y va en el tier `instant`: es lo que más cambia y lo que se coteja antes con el equipo (`profiles/ingeteam/oneplay_storage.py:240-252`).

Componente de cada clave (`profiles/ingeteam/oneplay_storage.py:39-69`): `inverter_state` y `active_power` en el inversor; `pv1_*` y `pv2_*` en `pv`; `battery_*` en `battery`; `grid_*` en `grid`; `load_power` en `load`.

Estados:

- `inverter_state` (Nota 2): `stopped`, `starting`, `off_grid`, `on_grid`, `on_grid_battery_standby`, `waiting_to_connect`, `critical_loads_bypassed`, `emergency_charge_pv`, `emergency_charge_grid`, `locked_waiting_reset`, `error` (`profiles/ingeteam/oneplay_storage.py:9-21`).
- `battery_state` (Nota 3): `standby`, `discharging`, `charging_constant_current`, `charging_constant_voltage`, `floating`, `equalizing`, `bms_communication_error`, `not_configured`, `calibration_step_1`, `calibration_step_2`, `standby_manual` (`profiles/ingeteam/oneplay_storage.py:24-36`).

### Extra

Definidas en `profiles/ingeteam/oneplay_storage.py:254-363` con `_extra` (`profiles/ingeteam/oneplay_storage.py:108-132`). Por defecto son diagnóstico (`entity_category=diagnostic`, rol `diagnostic`), están deshabilitadas y van en `slow`; cada una ajusta tier, activación y categoría.

| Clave | Registro | Tier | Componente | Por defecto |
|---|---|---|---|---|
| `operation_time` | 30007 (U32) | `slow` | inversor | deshabilitada |
| `battery_discharge_limit_reason` | 30030 | `normal` | `battery` | deshabilitada |
| `battery_charge_limit_reason` | 30078 | `normal` | `battery` | deshabilitada |
| `reactive_power` | 30039 | `fast` | inversor | deshabilitada |
| `power_factor` | 30040 | `fast` | inversor | deshabilitada |
| `power_reduction_ratio` | 30041 | `normal` | inversor | deshabilitada |
| `power_reduction_reason` | 30042 | `normal` | inversor | deshabilitada |
| `critical_load_voltage`, `_current`, `_frequency`, `_power` | 30044-30047 | `fast` | `critical_loads` | activas |
| `internal_meter_voltage`, `_current`, `_frequency`, `_power` | 30049-30052 | `fast` | `internal_meter` | activas |
| `dc_bus_voltage` | 30055 | `fast` | inversor | deshabilitada |
| `inverter_temperature` | 30058 (S16) | `normal` | inversor | deshabilitada |
| `isolation_positive`, `isolation_negative` | 30060, 30061 | `slow` | inversor | deshabilitadas |
| `external_pv_power` | 30080 | `fast` | `pv` | deshabilitada |
| `ev_charger_power` | 30081 (S16) | `fast` | `ev_charger` | activa |

Las que van activas por defecto (`critical_load_*`, `internal_meter_*`, `ev_charger_power`) no son diagnóstico: son entidades de primer nivel de su componente (`profiles/ingeteam/oneplay_storage.py:272-363`). El resto se activa desde la UI de HA.

Los motivos de las Notas 7 y 9 (`*_limit_reason`, `power_reduction_reason`) salen como valor numérico crudo.

### Batería: alarmas y estados del BMS

Catorce `binary_sensor` en el componente `battery`, uno por bit de dos registros (`ABH2010IMB08` págs. 6-8; `profiles/ingeteam/oneplay_storage.py:135-147`, `:364-378`). Van en el tier `fast`, con `entity_category=diagnostic` y activados por defecto. Cada uno se decodifica con `decode` sobre el bit (`domain/decode.py:27-28`) y se publica en `adapters/inbound/entities/binary_sensor.py:11-23`.

| Registro | Bits | Claves | Rol | Clase de HA |
|---|---|---|---|---|
| 30029 (alarmas) | 0-8 | `bms_alarm_high_charge_current`, `bms_alarm_high_voltage`, `bms_alarm_low_voltage`, `bms_alarm_high_temperature`, `bms_alarm_low_temperature`, `bms_alarm_internal`, `bms_alarm_cell_imbalance`, `bms_alarm_high_discharge_current`, `bms_alarm_system_error` | `bms_alarm` | `problem` |
| 30069 (estados) | 0-4 | `bms_stop_charge`, `bms_stop_discharge`, `bms_forced_charge`, `bms_calibration`, `bms_forced_charge_soc` | `bms_flag` | ninguna |

Un bit a 1 enciende la entidad. Los bits no listados no se publican.

### Energía calculada

`ABH2010IMB08` no trae contadores de energía. La integración integra la potencia (`profiles/ingeteam/oneplay_storage.py:380-418`). Decisión: [ADR 0009](../decisions/0009-computed-energy.md).

| Clave | Fuentes | Cuenta |
|---|---|---|
| `solar_energy` | `pv1_power` + `pv2_power` | potencia > 0 |
| `grid_import_energy` | `grid_power` | potencia > 0 |
| `grid_export_energy` | `grid_power` | potencia < 0, en valor absoluto |
| `battery_charge_energy` | `battery_power` | potencia < 0, en valor absoluto |
| `battery_discharge_energy` | `battery_power` | potencia > 0 |

- Sensores en kWh, `device_class=energy`, `state_class=total_increasing`, activos por defecto (`adapters/inbound/entities/energy.py:14-18`).
- Regla del trapecio sobre la suma de las fuentes, ya filtrada por signo (`domain/energy.py:39-51`).
- No se integra: un tramo con una lectura fallida o una fuente sin valor (`adapters/inbound/entities/energy.py:43-51`), ni un tramo de más de 3 intervalos del tier (`adapters/inbound/entities/energy.py:26`).
- Tras reiniciar o recargar, siguen desde el último total guardado. Lo que pasa con HA apagado no se cuenta (`adapters/inbound/entities/energy.py:27-33`).
- Las fuentes se leen aunque su sensor de potencia esté deshabilitado (`adapters/inbound/runtime.py:51-62`).
- `solar_energy` integra la potencia DC de los MPPT, antes de las pérdidas del inversor.

**Signos supuestos.** El PDF no documenta el signo de `grid_power` ni de `battery_power`. Se asume `grid_power` > 0 = importación y `battery_power` > 0 = descarga (`profiles/ingeteam/oneplay_storage.py:223`). Se verifica en la VM con diagnostics. Si el equipo dice otra cosa, se invierte el `sign` de las energías afectadas en el perfil.

Las escalas del PDF tampoco están verificadas en equipo, sobre todo `[A x100]`, `[Hz x10]` y `[V x 10]`.

## Sensores del 1Play TL M sin storage

Definidos en `profiles/ingeteam/oneplay.py:17-50`.

| Clave | Tipo | Unidad | Tier | Registro | Clases de HA |
|---|---|---|---|---|---|
| `inverter_state` | enum | — | `fast` | `0x101D` (U16) | `device_class=enum` |
| `active_power` | número | W | `fast` | `0x1037` (S32, escala 0,1) | `power`, `measurement` |
| `total_energy` | número | Wh | `normal` | `0x1021` (U32, escala 0,1) | `energy`, `total_increasing` |

Estados de `inverter_state` (`profiles/ingeteam/oneplay.py:26`): `0` `factory_default`, `1` `grid_disconnected`, `3` `grid_connected`. Solo estos tres están documentados en el PDF (nota 3).

La escala `[X x 10]` y el orden de palabras de los registros de 32 bits siguen sin verificar en equipo (`profiles/ingeteam/oneplay.py:32`, `:43`).

`inverter_state` es la misma clave de traducción en los dos perfiles: su bloque `state` de `strings.json` lleva la unión de las opciones de ambos.

## Sensor de irradiancia Si-RS485TC-…-MB

Definido en `profiles/mencke_tegtmeyer/si_rs485.py:7-68`. Modbus RTU tras una pasarela RS485 → Modbus TCP: para la integración es un equipo TCP más (puerto 502, unit ID 1 por defecto).

| Clave | Registro | Tipo | Escala | Unidad | Clases de HA |
|---|---|---|---|---|---|
| `irradiance` | 0 | U16 | 0,1 | W/m² | `irradiance`, `measurement` |
| `wind_speed` | 3 | U16 | 0,1 | m/s | `wind_speed`, `measurement` |
| `cell_temperature` | 7 | S16 | 0,1 | °C | `temperature`, `measurement` |
| `external_temperature` | 8 | S16 | 0,1 | °C | `temperature`, `measurement` |

- Todas `fast`, FC04, activas por defecto. `max_gap=3` las agrupa en un solo bloque de 9 registros: un ciclo es una petición (`si_rs485.py:16`).
- Los registros 7 y 8 exigen firmware ≥ 1.53 (`Specification` pág. 1).
- `external_temperature` mide el ambiente o el módulo según el modelo (`Specification` pág. 5).
- Un registro opcional ausente devuelve 0: los modelos sin viento o sin temperatura externa muestran 0 como si fuera una medida. Deshabilitar la entidad desde la UI (ADR [0013](../decisions/0013-sensor-series-profile.md)).
- Las escalas del PDF no están verificadas en equipo.

## Disponibilidad

- Cada tier lee todos sus registros o falla entero. Si la lectura falla (`DeviceUnavailable` o `DeviceProtocolError`), el coordinator lanza `UpdateFailed` y las entidades del tier pasan a `unavailable` (`adapters/inbound/coordinator.py:56-60`).
- Vuelven en la siguiente lectura correcta, sin intervención. El log de pérdida (`error`) y de recuperación (`info`) lo emite `DataUpdateCoordinator`, una vez por cambio de estado y no en cada tick (`adapters/inbound/coordinator.py:59`).
- Un equipo caído al arrancar no bloquea la entry: no se lanza `ConfigEntryNotReady` y el primer refresh va en segundo plano (`__init__.py:71-73`). Las entidades nacen `unavailable` hasta su primera lectura correcta (`adapters/inbound/entities/base.py:62-65`).
- Un segundo cliente Modbus (por ejemplo, el EMS) va contra la recomendación de Ingeteam y su efecto no está verificado. Ver [setup](../guides/setup.md).

## Valor fuera del enum

Un valor de un enum que no está en el perfil lanza `DecodeError` (`domain/decode.py:30-31`). Solo afecta a esa entidad: su valor es `None` (`unknown`) y el resto del tier sigue en pie (`application/poller.py:37-42`). El coordinator avisa con un `warning` una sola vez por clave hasta que el valor vuelve a decodificar bien (`adapters/inbound/coordinator.py:61-65`).

## Panel de Energía

- **STORAGE:** `solar_energy` como producción solar; `grid_import_energy` y `grid_export_energy` como consumo de red y retorno a red; `battery_charge_energy` y `battery_discharge_energy` como energía que entra y sale de la batería. Sin probar todavía en la VM.
- **1Play sin storage:** `total_energy` como producción solar (`profiles/ingeteam/oneplay.py:46-48`).

## Diagnostics

Se descarga desde HA con «Download diagnostics», en la página de la entry o en la del dispositivo. Los dos dan lo mismo: cada entry tiene un solo equipo (`diagnostics.py:12-19`).

Contenido (`adapters/inbound/diagnostics.py:15-44`):

- `profile` e `intervals`;
- `tiers`: `last_update_success`, `last_error` y `last_error_at` de cada tier;
- `entities`: por clave, `address`, `dtype`, `word_order`, `scale`, `raw` (palabras sin decodificar) y `value` decodificado (`adapters/inbound/diagnostics.py:30-37`);
- `entry`: los datos de la entry con `host` y `serial_number` ocultos por `async_redact_data` (`adapters/inbound/diagnostics.py:12`, `:39`).

Uso: en la VM, comparar `raw`, `scale` y `word_order` con el valor real del equipo para verificar escalas, orden de palabras y signos.
