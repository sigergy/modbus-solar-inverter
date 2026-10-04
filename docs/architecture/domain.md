# Arquitectura: domain

Documento vivo. Solo stdlib: no importa `homeassistant`, `modbus_connection` ni otras capas (`pyproject.toml:35-44`). Rutas bajo `custom_components/modbus_solar/domain/`.

## `types.py`

Enumeraciones del dominio. Sus valores se guardan en config y diagnostics: no se cambian (`types.py:1`).

| Tipo | Valores | Cita |
|---|---|---|
| `DataType` | `u16`, `s16`, `u32`, `s32`; propiedades `words` y `signed` | `types.py:6-19` |
| `RegisterKind` | `holding`, `input` | `types.py:22-24` |
| `PollTier` | `fast`, `normal`, `slow` | `types.py:27-30` |
| `Role` | `inverter_state`, `ac_power`, `energy_produced_total`; roles por magnitud del STORAGE (`pv_*`, `battery_*`, `grid_*`, `load_power`), `diagnostic` para entidades sin significado común entre marcas cinco `energy_*` para energías calculadas `export_limit` y `export_enabled` para el control del vertido, y `irradiance`, `wind_speed`, `cell_temperature` y `external_temperature` para el sensor de irradiancia | `types.py:33-64`, `:53`, `:54-58`, `:59-60`, `:61-64` |
| `Platform` | `sensor` | `types.py:67-68` |
| `WordOrder` | `big` (palabra alta primero), `little` | `types.py:71-75` |

## `profile.py`

Modelo de perfil de equipo. Tres `dataclass` inmutables y `kw_only`; los controles escribibles se declaran en `control.py`.

- `RegisterSpec(address, kind=HOLDING, dtype, scale=1.0, offset=0.0, word_order=BIG)` (`profile.py:11-18`).
- `EntitySpec(key, role, platform, register, poll, device_class=None, state_class=None, unit=None, enum=None, entity_category=None, enabled_default=True)` (`profile.py:21-33`). `device_class`, `state_class` y `entity_category` son cadenas: `domain` no importa HA (`profile.py:28`). `key` es también `translation_key` y sufijo del `unique_id` (`profile.py:23`).
- `DeviceProfile(id, brand, device_type, models, min_request_interval_s, max_block_registers=125, max_gap=0, default_port, default_unit_id, probe_key, entities, energies=(), controls=())` (`profile.py:36-50`). `125` es el límite de FC03/FC04 (`profile.py:43`). `max_gap`: huecos de hasta `max_gap` registros se leen dentro del mismo bloque (`profile.py:44`). `energies`: contadores calculados por la integración, ver `energy.py` (`profile.py:49`). `controls`: parámetros escribibles del equipo, ver `control.py` (`profile.py:50`).

## `energy.py`

Energía calculada: integra la potencia leída cuando el equipo no da contadores (`energy.py:1`).

- `SignFilter`: `positive` o `negative`; la parte negativa cuenta en valor absoluto (`energy.py:9-13`).
- `EnergySpec(key, role, sources, sign, enabled_default=True)`, `dataclass` inmutable y `kw_only` (`energy.py:16-22`). `sources` son claves de entidades de potencia en W y se suman (`energy.py:20`).
- `EnergyAccumulator(sign, max_gap_s, total_kwh=0.0)` (`energy.py:25-32`). Un `total_kwh` inicial negativo queda en 0 (`energy.py:31`).
  - `add(t, power_w)` integra por la regla del trapecio en kWh (`energy.py:38-50`).
  - `power_w = None` corta la serie: el tramo siguiente no se integra (`energy.py:39-42`).
  - Un tramo de más de `max_gap_s` o con `t` que retrocede no se integra (`energy.py:47-49`). El total nunca baja.
  - `total_kwh`: propiedad de solo lectura (`energy.py:34-36`).

## `control.py`

Parámetros escribibles: un límite con un interruptor que lo activa (`control.py:1`).

- `WriteSpec(address, prefix, dtype=S16, scale=1.0)`, `dataclass` inmutable y `kw_only` (`control.py:8-13`). `prefix` son las palabras fijas que van antes del valor, código de comando y dato 1 (`control.py:11`). La palabra del valor es `round(valor / scale)` (`control.py:13`).
- `GatedLimitSpec(key, switch_key, role, switch_role, write, min_value, max_value, step, unit, default, off_value=0.0, device_class=None, enabled_default=True)` (`control.py:16-30`). Una sola declaración da dos entidades: `key` es el number y `switch_key` el switch (`control.py:18-19`). `default` es el límite inicial si no hay valor restaurado (`control.py:27`). `off_value` es lo que se escribe al apagar el switch (`control.py:28`). `device_class` es una cadena: `domain` no importa HA (`control.py:29`).
- `GatedState(limit, enabled=True)`, `dataclass` mutable: el estado en memoria que comparten el number y el switch (`control.py:33-38`). `effective(spec)` devuelve lo que el equipo debe tener: `limit` con el switch activo, `spec.off_value` con el switch apagado (`control.py:40-42`).

## `errors.py`

| Error | Significado | Cita |
|---|---|---|
| `DeviceUnavailable` | El equipo no responde: sin conexión o tiempo agotado | `errors.py:4-5` |
| `DeviceProtocolError` | Excepción Modbus o trama inválida | `errors.py:8-9` |
| `DecodeError` | Las palabras leídas no dan un valor válido para la entidad | `errors.py:12-13` |
| `EncodeError` | El valor no cabe en el tipo de la escritura | `errors.py:16-17` |
| `EndpointInUse` | El endpoint ya está abierto con otros parámetros de enlace | `errors.py:20-21` |

Solo el gateway conoce las excepciones de `modbus_connection` (`errors.py:1`).

## `decode.py`

Palabras de 16 bits a valor de la entidad.

`decode(entity: EntitySpec, words: Sequence[int]) -> int | float | str` (`decode.py:10`).

- Lanza `DecodeError` si el número de palabras no es `dtype.words` (`decode.py:13-14`), si una palabra está fuera de `0..0xFFFF` (`decode.py:15-17`) o si el valor no está en `enum` (`decode.py:27-29`).
- `WordOrder.LITTLE` invierte las palabras antes de componer (`decode.py:19`).
- Los tipos con signo restan `2**bits` al pasar del máximo positivo (`decode.py:24-25`).
- Con `enum` devuelve el nombre del estado (`decode.py:30`). Sin escala ni offset devuelve el entero (`decode.py:31-32`). Con escala devuelve `round(raw * scale + offset, 6)` (`decode.py:34`).

## `encode.py`

Valor de la entidad a palabras de 16 bits: el inverso de `decode` (`encode.py:1`).

`encode(spec: WriteSpec, value: float) -> tuple[int, ...]` (`encode.py:9`).

- Lanza `EncodeError` si el tipo ocupa más de una palabra (`encode.py:10-11`), si el valor no es finito (`encode.py:12-13`) o si `round(value / scale)` no cabe en el tipo (`encode.py:14-17`).
- Los negativos van en complemento a dos de 16 bits (`encode.py:18-19`).
- Devuelve `(*spec.prefix, palabra)`: la trama completa de una escritura FC16 (`encode.py:19`).

## `blocks.py`

Agrupado de registros en bloques de lectura (una petición Modbus por bloque).

- `Block(kind, address, count)`, `dataclass` inmutable (`blocks.py:10-14`).
- `plan_blocks(registers: Iterable[RegisterSpec], max_gap: int, max_count: int) -> list[Block]` (`blocks.py:17`).
- Ordena por `(kind, address)` sin duplicados (`blocks.py:19`) y fusiona con el bloque anterior si es del mismo tipo, el hueco cabe en `max_gap` y el bloque cabe en `max_count` (`blocks.py:26-29`).

## `validate.py`

Comprobaciones estáticas de un perfil. Lista vacía = perfil válido (`validate.py:1`).

`validate_profile(profile: DeviceProfile) -> list[str]` (`validate.py:48`). Informa de:

- claves duplicadas (`validate.py:51-55`);
- `probe_key` que no existe (`validate.py:56-57`);
- energía con clave duplicada, también contra las entidades (`validate.py:60-63`);
- energía con una fuente que no existe o que no es de potencia, `device_class != "power"` (`validate.py:64-69`);
- energía con fuentes en tiers distintos: su sensor se suscribe a un solo coordinator (`validate.py:70-72`);
- control con la clave del number o la del switch duplicada, también contra las entidades y las energías (`validate.py:74-78`);
- control mal formado, `_control_problems` (`validate.py:17-45`, llamada en `:79`): `min_value` mayor que `max_value`, `step` no positivo, `default` u `off_value` fuera de rango, `scale == 0`, tipo de más de 16 bits, trama más larga que `max_block_registers`, palabra del prefijo fuera de `0..0xFFFF`, y extremos del rango u `off_value` que no codifican;
- registros solapados del mismo tipo (`validate.py:81-83`, `:12-14`);
- `enum` sin `device_class == "enum"` y al revés (`validate.py:88-91`);
- `scale == 0` (`validate.py:92-93`);
- `word_order` distinto de `BIG` en un tipo de 16 bits (`validate.py:94-95`).
