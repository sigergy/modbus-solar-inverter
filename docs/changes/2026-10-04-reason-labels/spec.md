---
type: feature
area: profiles
layers: [domain, adapters, profiles]
status: draft
date: 2026-10-04
---

# Spec 5 — Motivos con etiqueta traducida y código delante

Rutas bajo `custom_components/modbus_solar/` salvo indicación. Maqueta: [proposal.html](proposal.html).

## 1. Objetivo y alcance

El perfil `ingeteam.oneplay_storage` publica tres motivos como número crudo
(`profiles/ingeteam/oneplay_storage.py:198-200`, `:205-206`; `docs/features/monitoring.md:54`):

| Clave | Registro | Nota | Hoy |
|---|---|---|---|
| `power_reduction_reason` | 30042 | 7 | `16` |
| `battery_charge_limit_reason` | 30078 | 9 | `6` |
| `battery_discharge_limit_reason` | 30030 | 9 | `0` |

Con esta spec pasan a sensores `enum` traducidos, con el código delante de la etiqueta:
`16 - Excedente FV a red`. El código delante permite cotejar el valor con el PDF y con el soporte de
Ingeteam.

**Dentro:**
- Los tres motivos de la tabla, como sensores `enum`.
- Entidad nueva `reactive_setpoint_type` (30043, Nota 8), con el mismo formato.
- Textos `en` y `es` de las cuatro.

**Fuera:**
- Paradas y alarmas del inversor (30010, 30011, 30013-30015): su tabla solo está en `ABH2010IMC14`, que no
  está en el repo (`docs/wiki/brands/ingeteam/README.md`).
- Bits del BMS (30029, 30069) y componentes por dispositivo: spec 4,
  [setup-flow-v2](../2026-10-04-setup-flow-v2/spec.md).
- Registros 30074-30077 (Nota 11): el fabricante de la batería define los códigos.
- El perfil 1Play TL M sin storage: no tiene estos registros.

Fuente de todas las tablas: `ABH2010IMB08` rev. _I (23/04/2025), págs. 7-8
(`docs/wiki/brands/ingeteam/storage-1-play-tl-m/ABH2010IMB08.pdf`).

## 2. Decisiones

| Tema | Decisión |
|---|---|
| Formato | `<código> - <etiqueta>`, con el código del PDF. Lo pone la traducción, no el código Python |
| Plataforma | `sensor` con `device_class` `enum`, como `inverter_state` (`profiles/ingeteam/oneplay_storage.py:111-119`) |
| Código fuera de tabla | El sensor queda en «Desconocido» y el tier sigue (`application/poller.py:39-42`) |
| Nota 8 | Entidad nueva, extra: diagnóstico, desactivada por defecto y tier lento. Las otras tres pasan al tier normal en [setup-flow-v2](../2026-10-04-setup-flow-v2/spec.md) §5.7 |
| Charge y discharge | Comparten la tabla de la Nota 9 y las mismas claves de opción |

## 3. Perfil

### 3.1 `_extra` acepta `enum`

`_extra` (`profiles/ingeteam/oneplay_storage.py:74-94`) gana el parámetro `enum: dict[int, str] | None = None`
y lo pasa a `EntitySpec`, como ya hace `_core` (`:59`, `:70`). Las cuatro entidades llevan
`device_class="enum"` y `state_class=None`: `domain/validate.py:87-91` exige `enum` y `device_class` `enum`
juntos.

### 3.2 Entidades

| Clave | Registro | Tabla | Cambio |
|---|---|---|---|
| `power_reduction_reason` | 30042 | `POWER_REDUCTION_REASONS` | pasa a `enum` |
| `reactive_setpoint_type` | 30043 | `REACTIVE_SETPOINT_TYPES` | nueva |
| `battery_charge_limit_reason` | 30078 | `BATTERY_LIMIT_REASONS` | pasa a `enum` |
| `battery_discharge_limit_reason` | 30030 | `BATTERY_LIMIT_REASONS` | pasa a `enum` |

Con los tiers de hoy, 30043 queda entre 30042 y 30044, ya en el tier lento: no añade peticiones
(`domain/blocks.py`). Con setup-flow-v2 §5.7, 30042 pasa a normal y 30044 a rápido: 30043 queda solo en el tier
lento y añade una petición, ya contada allí.

### 3.3 Tablas

Código y clave de opción de cada valor. Los textos `es` y `en` están en la wiki del modelo,
[registers-storage-1-play-tl-m.md](../../wiki/brands/ingeteam/storage-1-play-tl-m/registers-storage-1-play-tl-m.md), Notas 7, 8 y 9.

`POWER_REDUCTION_REASONS` (30042, Nota 7, pág. 7):

| Valor | Opción | PDF |
|---|---|---|
| 0 | `no_limitation` | No limitation |
| 1 | `communication` | Communication |
| 2 | `pcb_temperature` | PCB Temperature |
| 3 | `heat_sink_temperature` | Heat Sink Temperature |
| 4 | `pac_vs_fac` | Pac vs Fac Algorithm |
| 5 | `soft_start` | Soft Start |
| 6 | `charge_power_configured` | Charge Power Configured |
| 7 | `pv_surplus_to_loads` | PV Surplus injected to the Loads |
| 8 | `pac_vs_vac` | Pac vs Vac Algorithm |
| 9 | `battery_power_limited` | Battery Power Limited |
| 10 | `ac_grid_power_limited` | AC Grid Power Limited |
| 11 | `self_consumption` | Self-Consumption Mode |
| 12 | `high_bus_voltage` | High Bus Voltage Protection |
| 13 | `lvrt_hvrt` | LVRT or HVRT Process |
| 14 | `nominal_ac_current` | Nominal AC Current |
| 15 | `grid_consumption_protection` | Grid Consumption Protection |
| 16 | `pv_surplus_to_grid` | PV Surplus Injected to the Grid |

`REACTIVE_SETPOINT_TYPES` (30043, Nota 8, págs. 7-8):

| Valor | Opción | PDF |
|---|---|---|
| 0 | `cos_phi_configuration` | Cos() Configuration |
| 1 | `q_communication` | Qac Communication |
| 2 | `cos_phi_communication` | Cos() Communication |
| 3 | `q_vs_v` | Qac vs Vac Algorithm |
| 4 | `cos_phi_vs_p` | Cos() vs Pac Algorithm |

`BATTERY_LIMIT_REASONS` (30030 y 30078, Nota 9, pág. 8):

| Valor | Opción | PDF |
|---|---|---|
| 0 | `no_limitation` | No limitation |
| 1 | `heat_sink_temperature` | Heat Sink Temperature |
| 2 | `pt100_temperature` | PT100 Temperature |
| 3 | `low_bus_voltage` | Low Bus Voltage Protection |
| 4 | `battery_settings` | Battery Settings |
| 5 | `bms_communication` | BMS Communication |
| 6 | `soc_max_configured` | SOC Max Configured |
| 7 | `soc_min_configured` | SOC Min Configured |
| 8 | `max_battery_power` | Maximum Battery Power |
| 9 | `modbus_command` | Modbus Command |
| 10 | `digital_input_2` | Digital Input 2 |
| 11 | `digital_input_3` | Digital Input 3 |
| 12 | `pv_charge_schedule` | PV charging scheduling |
| 13 | `ems_strategy` | EMS Strategy |

## 4. Traducciones

- `entity.sensor.<clave>.state` en `strings.json`, `translations/en.json` y `translations/es.json`, con los
  textos de la wiki
  ([registers-storage-1-play-tl-m.md](../../wiki/brands/ingeteam/storage-1-play-tl-m/registers-storage-1-play-tl-m.md), Notas 7, 8 y 9).
  `en.json` es copia literal de `strings.json` (`tests/unit/test_translations.py:24`).
- `entity.sensor.reactive_setpoint_type.name`: «Tipo de consigna de reactiva» / «Reactive power set-point type».
- Las dos claves de la Nota 9 llevan el mismo bloque `state`, repetido.
- `tests/unit/test_translations.py:32-44` ya comprueba que cada bloque `state` es exactamente la unión de las
  opciones `enum` de los perfiles con esa clave.

## 5. Compatibilidad

- `unique_id` y `entity_id` no cambian: la clave es la misma (`adapters/inbound/entities/base.py:30`).
- Las tres entidades ya tienen `state_class=None`: no hay estadísticas a largo plazo que se rompan.
- El historial anterior conserva los estados numéricos (`16`). Los nuevos salen como opción del `enum`.
- `reactive_setpoint_type` se crea desactivada, como las demás extras.

## 6. Tests

- `tests/unit/test_storage_profile.py`:
  - `EXTRA` gana `reactive_setpoint_type`;
  - `test_classes`: `power_reduction_reason` pasa a `("enum", None)`; se añaden las otras tres;
  - `test_enums`: opciones y códigos de las tres tablas, en el orden del PDF.
- `tests/unit/test_decode.py`: un motivo con código fuera de tabla lanza `DecodeError`.
- `tests/unit/test_translations.py`: sin cambios; cubre los bloques `state` nuevos.
- Tests y lint en CI, no en local.

## 7. Documentación

- `docs/features/monitoring.md:54`: los motivos salen con etiqueta y código; `reactive_setpoint_type` en la
  lista de extras (`:52`).
- `docs/features/control.md:40`: el motivo 16 se ve como «16 - Excedente FV a red».
- `docs/wiki/brands/ingeteam/storage-1-play-tl-m/registers-storage-1-play-tl-m.md`: tablas de las Notas 7, 8 y 9, con los textos
  `es` y `en` (hecho).
- `docs/README.md`: fila del cambio en el índice.

## 8. Criterios de aceptación

- Los tres motivos muestran `<código> - <etiqueta>` en `es` y `en`.
- `reactive_setpoint_type` existe, desactivada por defecto, en el tier lento.
- Un código fuera de tabla deja el sensor en «Desconocido» sin cortar el tier.
- Tests y lint en verde en CI.

## 9. Por decidir

- Textos `es` y `en` de la wiki ([registers-storage-1-play-tl-m.md](../../wiki/brands/ingeteam/storage-1-play-tl-m/registers-storage-1-play-tl-m.md)):
  son propuesta. Del PDF salen el código y el texto original en inglés.
- Nota 9, código 2 («PT100 Temperature»): el PDF no dice dónde está la sonda. «Temperatura de la batería (PT100)»
  lo interpreta; la alternativa literal es «2 - Temperatura PT100».

## 10. Pendiente de verificar en la VM

- Que la tarjeta de entidad muestra el texto traducido completo, con el código delante.
