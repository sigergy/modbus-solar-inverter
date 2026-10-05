# Arquitectura: domain

Documento vivo. Solo stdlib: no importa `homeassistant`, `modbus_connection` ni otras capas (`pyproject.toml:35-44`). Rutas bajo `custom_components/modbus_solar/domain/`.

## `types.py`

Enumeraciones del dominio. Sus valores se guardan en config y diagnostics: no se cambian (`types.py:1`).

| Tipo | Valores | Cita |
|---|---|---|
| `DataType` | `u16`, `s16`, `u32`, `s32`, `ascii` (texto de N registros; N en `RegisterSpec.length`); propiedades `words` y `signed` | `types.py:6-22` |
| `RegisterKind` | `holding`, `input` | `types.py:25` |
| `PollTier` | `instant`, `fast`, `normal`, `slow`; `instant` va primero porque el formulario de intervalos recorre el enum en orden (ADR [0016](../decisions/0016-instant-tier.md)) | `types.py:30-34` |
| `Role` | `inverter_state`, `ac_power`, `energy_produced_total`; roles por magnitud del STORAGE (`pv_*`, `battery_*`, `grid_*`, `load_power`), `diagnostic` para entidades sin significado común entre marcas, `bms_alarm` y `bms_flag` para los bits del BMS, cinco `energy_*` para energías calculadas, `export_limit` y `export_enabled` para el control del vertido, y `irradiance`, `wind_speed`, `cell_temperature` y `external_temperature` para el sensor de irradiancia | `types.py:37-70` |
| `Component` | la parte física del equipo a la que pertenece una entidad, y con ella su dispositivo de HA (ADR [0015](../decisions/0015-device-per-component.md)) | `types.py:73-83` |
| `Platform` | `sensor`, `binary_sensor` | `types.py:86-88` |
| `WordOrder` | `big` (palabra alta primero), `little` | `types.py:91-95` |

## `profile.py`

Modelo de perfil de equipo. `dataclass` inmutables y `kw_only`; los controles escribibles se declaran en `control.py`.

- `RegisterSpec(address, kind=HOLDING, dtype, scale=1.0, offset=0.0, word_order=BIG, length=0)` (`profile.py:11-23`). `length` son los registros del texto y solo cuenta con `DataType.ASCII`. La propiedad `words` da las palabras que ocupa el registro.
- `ComponentSpec(component, default=True)` (`profile.py:26-30`): un componente opcional del perfil. `default` dice si sale marcado en el alta.
- `EntitySpec(key, role, platform, register, poll, device_class=None, state_class=None, unit=None, enum=None, entity_category=None, enabled_default=True, bit=None, component=MAIN)` (`profile.py:33-47`). `device_class`, `state_class` y `entity_category` son cadenas: `domain` no importa HA. `key` es también `translation_key` y sufijo del `unique_id`. `bit` elige un bit de un registro `u16` y exige `platform=binary_sensor`. `component` es el dispositivo donde vive la entidad.
- `DeviceProfile(id, brand, device_type, models, min_request_interval_s, max_block_registers=125, max_gap=0, default_port, default_unit_id, probe_key, entities, energies=(), controls=(), serial=None, components=())` (`profile.py:50-67`). `125` es el límite de FC03/FC04. `max_gap`: huecos de hasta `max_gap` registros se leen dentro del mismo bloque. `energies`: contadores calculados por la integración, ver `energy.py`. `controls`: parámetros escribibles del equipo, ver `control.py`. `serial`: registro ASCII con el número de serie, opcional. `components`: componentes opcionales; `main` es implícito.

## `energy.py`

Energía calculada: integra la potencia leída cuando el equipo no da contadores (`energy.py:1`).

- `SignFilter`: `positive` o `negative`; la parte negativa cuenta en valor absoluto (`energy.py:9-13`).
- `EnergySpec(key, role, sources, sign, enabled_default=True, component=MAIN)`, `dataclass` inmutable y `kw_only` (`energy.py:16-23`). `sources` son claves de entidades de potencia en W y se suman (`energy.py:20`).
- `EnergyAccumulator(sign, max_gap_s, total_kwh=0.0)` (`energy.py:26-33`). Un `total_kwh` inicial negativo queda en 0 (`energy.py:32`).
  - `add(t, power_w)` integra por la regla del trapecio en kWh (`energy.py:39-51`).
  - `power_w = None` corta la serie: el tramo siguiente no se integra (`energy.py:40-43`).
  - Un tramo de más de `max_gap_s` o con `t` que retrocede no se integra (`energy.py:48-49`). El total nunca baja.
  - `total_kwh`: propiedad de solo lectura (`energy.py:35-37`).

## `control.py`

Parámetros escribibles: un límite con un interruptor que lo activa (`control.py:1`).

- `WriteSpec(address, prefix, dtype=S16, scale=1.0)`, `dataclass` inmutable y `kw_only` (`control.py:8-13`). `prefix` son las palabras fijas que van antes del valor, código de comando y dato 1 (`control.py:11`). La palabra del valor es `round(valor / scale)` (`control.py:13`).
- `GatedLimitSpec(key, switch_key, role, switch_role, write, min_value, max_value, step, unit, default, off_value=0.0, device_class=None, enabled_default=True, component=MAIN)` (`control.py:16-31`). Una sola declaración da dos entidades: `key` es el number y `switch_key` el switch (`control.py:18-19`). `default` es el límite inicial si no hay valor restaurado (`control.py:27`). `off_value` es lo que se escribe al apagar el switch (`control.py:28`). `device_class` es una cadena: `domain` no importa HA (`control.py:29`).
- `GatedState(limit, enabled=True)`, `dataclass` mutable: el estado en memoria que comparten el number y el switch (`control.py:34-39`). `effective(spec)` devuelve lo que el equipo debe tener: `limit` con el switch activo, `spec.off_value` con el switch apagado (`control.py:41-43`).

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

`decode(entity: EntitySpec, words: Sequence[int]) -> int | float | str | bool` (`decode.py:10`).

- Lanza `DecodeError` si el número de palabras no es `register.words` (`decode.py:13-14`), si una palabra está fuera de `0..0xFFFF` (`decode.py:15-17`) o si el valor no está en `enum`.
- `WordOrder.LITTLE` invierte las palabras antes de componer (`decode.py:19`).
- Los tipos con signo restan `2**bits` al pasar del máximo positivo (`decode.py:24-25`).
- Con `bit` devuelve el `bool` de ese bit (`decode.py:27-28`). Con `enum` devuelve el nombre del estado (`decode.py:29-32`). Sin escala ni offset devuelve el entero (`decode.py:33-34`). Con escala devuelve `round(raw * scale + offset, 6)` (`decode.py:35-36`).

`decode_text(register: RegisterSpec, words: Sequence[int]) -> str` (`decode.py:39-44`) decodifica el número de serie: dos caracteres ASCII por palabra, sin nulos ni espacios al final.

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

`validate_profile(profile: DeviceProfile) -> list[str]` (`validate.py:69`). Informa de:

- claves duplicadas (`validate.py:73-76`);
- `probe_key` que no existe (`validate.py:77-78`);
- energía con clave duplicada, también contra las entidades (`validate.py:81-84`);
- energía con una fuente que no existe o que no es de potencia, `device_class != "power"` (`validate.py:85-90`);
- energía en un componente distinto del de sus fuentes (`validate.py:91-93`);
- energía con fuentes en tiers distintos: su sensor se suscribe a un solo coordinator (`validate.py:94-96`);
- control con la clave del number o la del switch duplicada, también contra las entidades y las energías (`validate.py:98-102`);
- control mal formado, `_control_problems` (`validate.py:17-45`, llamada en `:103`): `min_value` mayor que `max_value`, `step` no positivo, `default` u `off_value` fuera de rango, `scale == 0`, tipo de más de 16 bits, trama más larga que `max_block_registers`, palabra del prefijo fuera de `0..0xFFFF`, y extremos del rango u `off_value` que no codifican;
- componentes mal declarados, `_component_problems` (`validate.py:48-66`, llamada en `:105`): `main` declarado, componente repetido, entidad con un componente sin declarar y componente declarado sin entidades;
- registros solapados del mismo tipo, salvo dos bits del mismo registro (`validate.py:107-112`, `:12-14`);
- `enum` sin `device_class == "enum"` y al revés (`validate.py:117-120`);
- `ascii` en una entidad: solo vale para `serial` (`validate.py:121-123`);
- `bit` en una entidad que no es `binary_sensor` ni `u16`, o fuera de 0-15, y `binary_sensor` sin `bit` (`validate.py:124-132`);
- `scale == 0` (`validate.py:133-134`);
- `word_order` distinto de `BIG` en un tipo de 16 bits (`validate.py:135-136`);
- `serial` que no es `ascii` o con `length < 1` (`validate.py:137-141`).
