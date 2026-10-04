# Funcionalidad: monitorización

Documento vivo. Rutas bajo `custom_components/modbus_solar/` salvo indicación. Nombres de las entidades en `strings.json:57-224`.

## Perfiles

| Perfil | Equipo | Mapa | Fichero |
|---|---|---|---|
| `ingeteam.oneplay_storage` | INGECON SUN STORAGE 1Play TL M | `ABH2010IMB08`: input registers 30001-30081, FC04 ([registers.md](../wiki/brands/ingeteam/storage-1-play-tl-m/registers.md)) | `profiles/ingeteam/oneplay_storage.py` |
| `ingeteam.oneplay` | INGECON SUN 1Play TL M, sin storage | `ACL2010IMB05`: holding `0x10xx`, FC03 ([registers.md](../wiki/brands/ingeteam/1-play-tl-m/registers.md)) | `profiles/ingeteam/oneplay.py` |

Los dos van en el catálogo (`profiles/__init__.py:7`).

## Sensores del STORAGE 1Play TL M

Todos son input registers. Dirección = registro − 30001 (`profiles/ingeteam/oneplay_storage.py:38-40`).

### Núcleo (activos)

Definidos en `profiles/ingeteam/oneplay_storage.py:104-183`. Potencia, tensión, corriente, frecuencia y temperatura llevan `state_class=measurement`.

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
| `grid_voltage` | 30070 | U16 | 1 | V | `normal` |
| `grid_frequency` | 30071 | U16 | 0,1 | Hz | `normal` |
| `grid_power` | 30072 | S16 | 1 | W | `fast` |
| `load_power` | 30079 | U16 | 1 | W | `fast` |

La red se lee del vatímetro externo (30070-30073).

Estados:

- `inverter_state` (Nota 2): `stopped`, `starting`, `off_grid`, `on_grid`, `on_grid_battery_standby`, `waiting_to_connect`, `critical_loads_bypassed`, `emergency_charge_pv`, `emergency_charge_grid`, `locked_waiting_reset`, `error` (`profiles/ingeteam/oneplay_storage.py:8-20`).
- `battery_state` (Nota 3): `standby`, `discharging`, `charging_constant_current`, `charging_constant_voltage`, `floating`, `equalizing`, `bms_communication_error`, `not_configured`, `calibration_step_1`, `calibration_step_2`, `standby_manual` (`profiles/ingeteam/oneplay_storage.py:23-35`).

### Extra (deshabilitadas por defecto)

Definidas en `profiles/ingeteam/oneplay_storage.py:184-213`. Todas en el tier `slow`, con `entity_category=diagnostic` y rol `diagnostic` (`profiles/ingeteam/oneplay_storage.py:67-87`). Se activan desde la UI de HA.

`operation_time`, `battery_discharge_limit_reason`, `battery_charge_limit_reason`, `reactive_power`, `power_factor`, `power_reduction_ratio`, `power_reduction_reason`, `critical_load_voltage`, `critical_load_current`, `critical_load_frequency`, `critical_load_power`, `internal_meter_voltage`, `internal_meter_current`, `internal_meter_frequency`, `internal_meter_power`, `dc_bus_voltage`, `inverter_temperature`, `isolation_positive`, `isolation_negative`, `external_pv_power`, `ev_charger_power`.

Los motivos de las Notas 7 y 9 (`*_limit_reason`, `power_reduction_reason`) salen como valor numérico crudo.

### Energía calculada

`ABH2010IMB08` no trae contadores de energía. La integración integra la potencia (`profiles/ingeteam/oneplay_storage.py:215-242`). Decisión: [ADR 0009](../decisions/0009-computed-energy.md).

| Clave | Fuentes | Cuenta |
|---|---|---|
| `solar_energy` | `pv1_power` + `pv2_power` | potencia > 0 |
| `grid_import_energy` | `grid_power` | potencia > 0 |
| `grid_export_energy` | `grid_power` | potencia < 0, en valor absoluto |
| `battery_charge_energy` | `battery_power` | potencia < 0, en valor absoluto |
| `battery_discharge_energy` | `battery_power` | potencia > 0 |

- Sensores en kWh, `device_class=energy`, `state_class=total_increasing`, activos por defecto (`adapters/inbound/entities/energy.py:14-18`).
- Regla del trapecio sobre la suma de las fuentes, ya filtrada por signo (`domain/energy.py:38-50`).
- No se integra: un tramo con una lectura fallida o una fuente sin valor (`adapters/inbound/entities/energy.py:45-53`), ni un tramo de más de 3 intervalos del tier (`adapters/inbound/entities/energy.py:26`).
- Tras reiniciar o recargar, siguen desde el último total guardado. Lo que pasa con HA apagado no se cuenta (`adapters/inbound/entities/energy.py:29-35`).
- Las fuentes se leen aunque su sensor de potencia esté deshabilitado (`adapters/inbound/runtime.py:44-54`).
- `solar_energy` integra la potencia DC de los MPPT, antes de las pérdidas del inversor.

**Signos supuestos.** El PDF no documenta el signo de `grid_power` ni de `battery_power`. Se asume `grid_power` > 0 = importación y `battery_power` > 0 = descarga (`profiles/ingeteam/oneplay_storage.py:216`). Se verifica en la VM con diagnostics. Si el equipo dice otra cosa, se invierte el `sign` de las energías afectadas en el perfil.

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

## Disponibilidad

- Cada tier lee todos sus registros o falla entero. Si la lectura falla (`DeviceUnavailable` o `DeviceProtocolError`), el coordinator lanza `UpdateFailed` y las entidades del tier pasan a `unavailable` (`adapters/inbound/coordinator.py:56-60`).
- Vuelven en la siguiente lectura correcta, sin intervención. El log de pérdida (`error`) y de recuperación (`info`) lo emite `DataUpdateCoordinator`, una vez por cambio de estado y no en cada tick (`adapters/inbound/coordinator.py:59`).
- Un equipo caído al arrancar no bloquea la entry: no se lanza `ConfigEntryNotReady` y el primer refresh va en segundo plano (`__init__.py:34-36`). Las entidades nacen `unavailable` hasta su primera lectura correcta (`adapters/inbound/entities/base.py:34-37`).
- Un segundo cliente Modbus (por ejemplo, el EMS) va contra la recomendación de Ingeteam y su efecto no está verificado. Ver [setup](../guides/setup.md).

## Valor fuera del enum

Un valor de un enum que no está en el perfil lanza `DecodeError` (`domain/decode.py:28-29`). Solo afecta a esa entidad: su valor es `None` (`unknown`) y el resto del tier sigue en pie (`application/poller.py:37-42`). El coordinator avisa con un `warning` una sola vez por clave hasta que el valor vuelve a decodificar bien (`adapters/inbound/coordinator.py:61-65`).

## Panel de Energía

- **STORAGE:** `solar_energy` como producción solar; `grid_import_energy` y `grid_export_energy` como consumo de red y retorno a red; `battery_charge_energy` y `battery_discharge_energy` como energía que entra y sale de la batería. Sin probar todavía en la VM.
- **1Play sin storage:** `total_energy` como producción solar (`profiles/ingeteam/oneplay.py:46-48`).

## Diagnostics

Se descarga desde HA con «Download diagnostics», en la página de la entry o en la del dispositivo. Los dos dan lo mismo: cada entry tiene un solo equipo (`diagnostics.py:12-19`).

Contenido (`adapters/inbound/diagnostics.py:14-43`):

- `profile` e `intervals`;
- `tiers`: `last_update_success`, `last_error` y `last_error_at` de cada tier;
- `entities`: por clave, `address`, `dtype`, `word_order`, `scale`, `raw` (palabras sin decodificar) y `value` decodificado (`adapters/inbound/diagnostics.py:30-35`);
- `entry`: los datos de la entry con `host` oculto por `async_redact_data` (`adapters/inbound/diagnostics.py:11`, `:38`).

Uso: en la VM, comparar `raw`, `scale` y `word_order` con el valor real del equipo para verificar escalas, orden de palabras y signos.
