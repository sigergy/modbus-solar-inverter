# Arquitectura: domain

Documento vivo. Solo stdlib: no importa `homeassistant`, `modbus_connection` ni otras capas (`pyproject.toml:35-44`). Rutas bajo `custom_components/modbus_solar/domain/`.

## `types.py`

Enumeraciones del dominio. Sus valores se guardan en config y diagnostics: no se cambian (`types.py:1`).

| Tipo | Valores | Cita |
|---|---|---|
| `DataType` | `u16`, `s16`, `u32`, `s32`; propiedades `words` y `signed` | `types.py:6-19` |
| `RegisterKind` | `holding`, `input` | `types.py:22-24` |
| `PollTier` | `fast`, `normal`, `slow` | `types.py:27-30` |
| `Role` | `inverter_state`, `ac_power`, `energy_produced_total` | `types.py:33-38` |
| `Platform` | `sensor` | `types.py:41-42` |
| `WordOrder` | `big` (palabra alta primero), `little` | `types.py:45-49` |

## `profile.py`

Modelo de perfil de equipo. Tres `dataclass` inmutables y `kw_only`.

- `RegisterSpec(address, kind=HOLDING, dtype, scale=1.0, offset=0.0, word_order=BIG)` (`profile.py:9-16`).
- `EntitySpec(key, role, platform, register, poll, device_class=None, state_class=None, unit=None, enum=None, entity_category=None, enabled_default=True)` (`profile.py:19-31`). `device_class`, `state_class` y `entity_category` son cadenas: `domain` no importa HA (`profile.py:26`). `key` es también `translation_key` y sufijo del `unique_id` (`profile.py:21`).
- `DeviceProfile(id, brand, device_type, models, min_request_interval_s, max_block_registers=125, default_port, default_unit_id, probe_key, entities)` (`profile.py:34-45`). `125` es el límite de FC03/FC04 (`profile.py:41`).

## `errors.py`

| Error | Significado | Cita |
|---|---|---|
| `DeviceUnavailable` | El equipo no responde: sin conexión o tiempo agotado | `errors.py:4-5` |
| `DeviceProtocolError` | Excepción Modbus o trama inválida | `errors.py:8-9` |
| `DecodeError` | Las palabras leídas no dan un valor válido para la entidad | `errors.py:12-13` |
| `EndpointInUse` | El endpoint ya está abierto con otros parámetros de enlace | `errors.py:16-17` |

Solo el gateway conoce las excepciones de `modbus_connection` (`errors.py:1`).

## `decode.py`

Palabras de 16 bits a valor de la entidad.

`decode(entity: EntitySpec, words: Sequence[int]) -> int | float | str` (`decode.py:10`).

- Lanza `DecodeError` si el número de palabras no es `dtype.words` (`decode.py:13-14`), si una palabra está fuera de `0..0xFFFF` (`decode.py:15-17`) o si el valor no está en `enum` (`decode.py:27-29`).
- `WordOrder.LITTLE` invierte las palabras antes de componer (`decode.py:19`).
- Los tipos con signo restan `2**bits` al pasar del máximo positivo (`decode.py:24-25`).
- Con `enum` devuelve el nombre del estado (`decode.py:30`). Sin escala ni offset devuelve el entero (`decode.py:31-32`). Con escala devuelve `round(raw * scale + offset, 6)` (`decode.py:34`).

## `blocks.py`

Agrupado de registros en bloques de lectura (una petición Modbus por bloque).

- `Block(kind, address, count)`, `dataclass` inmutable (`blocks.py:10-14`).
- `plan_blocks(registers: Iterable[RegisterSpec], max_gap: int, max_count: int) -> list[Block]` (`blocks.py:17`).
- Ordena por `(kind, address)` sin duplicados (`blocks.py:19`) y fusiona con el bloque anterior si es del mismo tipo, el hueco cabe en `max_gap` y el bloque cabe en `max_count` (`blocks.py:26-29`).

## `validate.py`

Comprobaciones estáticas de un perfil. Lista vacía = perfil válido (`validate.py:1`).

`validate_profile(profile: DeviceProfile) -> list[str]` (`validate.py:14`). Informa de:

- claves duplicadas (`validate.py:18-21`);
- `probe_key` que no existe (`validate.py:22-23`);
- registros solapados del mismo tipo (`validate.py:25-27`, `:9-11`);
- `enum` sin `device_class == "enum"` y al revés (`validate.py:32-35`);
- `scale == 0` (`validate.py:36-37`);
- `word_order` distinto de `BIG` en un tipo de 16 bits (`validate.py:38-39`).
