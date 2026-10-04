---
type: feature
area: control
layers: [domain, ports, application, adapters, profiles]
status: in-progress
date: 2026-10-04
---

# Plan de implementación — Spec 3, escritura de parámetros y control del vertido

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `subagent-driven-development` (recomendada) o
> `executing-plans` para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** un switch y un number de vertido a red para el STORAGE 1Play TL M, sobre una ruta de
escritura Modbus genérica declarada en el perfil, según
`docs/changes/2026-10-04-export-control/spec.md`. Switch ON = vertido activado (escribe el valor
del number); switch OFF = vertido desactivado (escribe 0 W).

**Arquitectura:** el perfil declara un `GatedLimitSpec` (`domain/control.py`). `encode` convierte el
valor en palabras. Un puerto nuevo `DeviceWriter` lo escribe; `ModbusGateway` lo implementa con FC16
en una trama. Dos casos de uso (`set_limit`, `set_enabled`) mantienen un `GatedState` en memoria.
`number` y `switch` de HA comparten ese estado, que es optimista y restaurado (no hay registro de
lectura).

**Stack:** Python 3.14, Home Assistant 2026.9.4, `modbus-connection` 4.10.0, pytest +
`pytest-homeassistant-custom-component` 0.13.367, ruff, import-linter, GitHub Actions.

## Global Constraints

- Rama de trabajo: `feat/export-control`, creada desde `main`. Nunca commit en `main`.
- Push a `feat/export-control` autorizado sin confirmar (memoria `tests-ci-only`, 2026-10-04).
  Force push, merge, rebase y PR piden confirmación.
- **Tests solo en GitHub Actions.** Nunca `pytest` en la máquina Windows. RED y GREEN se
  comprueban con `bash scripts/ci-wait.sh`, lanzado con `run_in_background: true`.
- Gates locales antes de cada commit: `bash scripts/lint.sh` (ruff, import-linter, compileall).
  `.venv/` no se commitea.
- Commits RED (`test(red): …`) permitidos en la rama. Un commit GREEN por tarea con CI en verde.
- Todo commit termina con:
  ```
  Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01BSFWeYRgwtC2HrKVxZWY8W
  ```
- Comentarios del código en español. Identificadores, ficheros, logs, excepciones y
  `strings.json` en inglés. Ficheros nuevos de una o dos palabras en `snake_case` (módulos Python).
- Dentro de `custom_components/modbus_solar` solo imports relativos.
- Contratos de import-linter intactos: `domain`, `ports`, `application` y `profiles` no
  importan `homeassistant` ni `modbus_connection`; `profiles` solo importa `domain`.
- Escritura Ingeteam: FC16 en la dirección 1000, palabras `[26, 0x0A, vatios]` en una sola
  trama (`AAA0030IMB03_N` págs. 4, 7-8, 19-20). Rango del number: 0-6000 W, paso 1, por
  defecto 6000 W. Los negativos del PDF no se exponen.
- La restauración tras reiniciar HA **nunca** escribe al equipo.
- Identificadores estables: `unique_id` = `f"{entry_id}_{key}"` con `export_limit` y
  `export_enabled`.
- `graft/` y `.graft_*` nunca se commitean. El `.ignore` sin seguimiento no es de este cambio: no se añade.
- Ámbito: solo el vertido. Potencia contratada, otros parámetros de batería y lectura del ajuste
  quedan fuera (spec §1).
- No inventar: si una API no se comporta como dice el plan, parar y avisar con la salida real.

## Mapa de ficheros

Rutas de código relativas a `custom_components/modbus_solar/`.

| Fichero | Cambio | Tarea |
|---|---|---|
| `domain/control.py` | nuevo: `WriteSpec`, `GatedLimitSpec`, `GatedState` | 1 |
| `domain/encode.py` | nuevo: `encode` | 1 |
| `domain/errors.py` | `EncodeError` | 1 |
| `domain/types.py` | `Role.EXPORT_LIMIT`, `Role.EXPORT_ENABLED` | 1 |
| `domain/profile.py` | `DeviceProfile.controls` | 1 |
| `domain/validate.py` | comprobaciones de controles | 1 |
| `ports/device.py` | `DeviceWriter` | 2 |
| `application/control.py` | nuevo: `set_limit`, `set_enabled` | 2 |
| `adapters/outbound/modbus_gateway.py` | `write`; traducción de errores compartida con `read` | 2 |
| `profiles/ingeteam/oneplay_storage.py` | `_command` y `controls` | 3 |
| `adapters/inbound/runtime.py` | `writer`, `control_states`; `build_runtime(..., writer, keys)` | 4 |
| `adapters/inbound/entities/base.py` | acepta `GatedLimitSpec` y `key` explícita | 4 |
| `adapters/inbound/entities/control.py` | nuevo: `ModbusSolarControl`, `write_errors` | 4 |
| `adapters/inbound/entities/number.py` | nuevo: `ModbusSolarNumber` | 4 |
| `adapters/inbound/entities/switch.py` | nuevo: `ModbusSolarSwitch` | 5 |
| `adapters/inbound/entities/factory.py` | `build_numbers`, `build_switches` | 4, 5 |
| `number.py`, `switch.py` | nuevos: plataformas HA | 4, 5 |
| `__init__.py` | `PLATFORMS`, `writer` | 4, 5 |
| `strings.json`, `translations/{en,es}.json` | number, switch y `exceptions.write_failed` | 4, 5 |
| `tests/…` | ver cada tarea | 1-5 |
| `docs/…`, `README.md`, ADR 0011 y 0012 | documentación | 6 |

---

### Tarea 1: dominio, modelo, codificación y validación

**Files:**
- Create: `domain/control.py`, `domain/encode.py`
- Modify: `domain/errors.py`, `domain/types.py`, `domain/profile.py`, `domain/validate.py`
- Test: `tests/unit/test_encode.py` (nuevo), `tests/unit/test_control.py` (nuevo),
  `tests/unit/test_types.py`, `tests/unit/test_validate.py`

**Interfaces:**
- Produces:
  - `WriteSpec(address: int, prefix: tuple[int, ...], dtype: DataType = S16, scale: float = 1.0)`
  - `GatedLimitSpec(key, switch_key, role, switch_role, write, min_value, max_value, step, unit,
    default, off_value=0.0, device_class=None, enabled_default=True)`
  - `GatedState(limit: float, enabled: bool = True)` con `effective(spec) -> float`
  - `encode(spec: WriteSpec, value: float) -> tuple[int, ...]`; lanza `EncodeError`
  - `DeviceProfile.controls: tuple[GatedLimitSpec, ...] = ()`
  - `Role.EXPORT_LIMIT = "export_limit"`, `Role.EXPORT_ENABLED = "export_enabled"`

- [ ] **Step 1: tests que fallan.** Crear `tests/unit/test_encode.py`:

```python
"""encode: valor de la entidad -> palabras de 16 bits (inverso de decode)."""

import pytest

from custom_components.modbus_solar.domain.control import WriteSpec
from custom_components.modbus_solar.domain.encode import encode
from custom_components.modbus_solar.domain.errors import EncodeError
from custom_components.modbus_solar.domain.types import DataType

GRID_POWER = WriteSpec(address=1000, prefix=(26, 0x0A))


@pytest.mark.parametrize(
    ("value", "words"),
    [
        (0, (26, 10, 0)),
        (3000, (26, 10, 3000)),
        (6000, (26, 10, 6000)),
        (32767, (26, 10, 32767)),
        (-1, (26, 10, 0xFFFF)),
        (-6000, (26, 10, 0x10000 - 6000)),
        (-32768, (26, 10, 0x8000)),
    ],
)
def test_s16_value_to_words(value: float, words: tuple[int, ...]) -> None:
    assert encode(GRID_POWER, value) == words


def test_float_value_is_rounded() -> None:
    assert encode(GRID_POWER, 3000.4) == (26, 10, 3000)


def test_scale_divides_the_value() -> None:
    assert encode(WriteSpec(address=1, prefix=(), scale=0.1), 12.5) == (125,)


def test_u16_range() -> None:
    spec = WriteSpec(address=1, prefix=(), dtype=DataType.U16)
    assert encode(spec, 65535) == (65535,)
    with pytest.raises(EncodeError):
        encode(spec, -1)
    with pytest.raises(EncodeError):
        encode(spec, 65536)


@pytest.mark.parametrize("value", [32768, -32769, float("nan"), float("inf"), float("-inf")])
def test_value_that_does_not_fit_is_rejected(value: float) -> None:
    with pytest.raises(EncodeError):
        encode(GRID_POWER, value)


@pytest.mark.parametrize("dtype", [DataType.U32, DataType.S32])
def test_32_bit_types_are_not_supported(dtype: DataType) -> None:
    with pytest.raises(EncodeError):
        encode(WriteSpec(address=1, prefix=(), dtype=dtype), 1)
```

Crear `tests/unit/test_control.py`:

```python
"""Modelo de control: WriteSpec, GatedLimitSpec y GatedState."""

import dataclasses

import pytest

from custom_components.modbus_solar.domain.control import GatedLimitSpec, GatedState, WriteSpec
from custom_components.modbus_solar.domain.types import DataType, Role

SPEC = GatedLimitSpec(
    key="limit",
    switch_key="enabled",
    role=Role.EXPORT_LIMIT,
    switch_role=Role.EXPORT_ENABLED,
    write=WriteSpec(address=1000, prefix=(26, 10)),
    min_value=0,
    max_value=6000,
    step=1,
    unit="W",
    default=6000,
)


def test_write_spec_defaults() -> None:
    write = WriteSpec(address=1000, prefix=(26, 10))
    assert (write.dtype, write.scale) == (DataType.S16, 1.0)


def test_gated_limit_spec_defaults() -> None:
    assert (SPEC.off_value, SPEC.device_class, SPEC.enabled_default) == (0.0, None, True)


def test_specs_are_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        SPEC.max_value = 1  # type: ignore[misc]


def test_state_starts_enabled() -> None:
    assert GatedState(limit=3000).enabled is True


def test_effective_is_the_limit_when_enabled() -> None:
    assert GatedState(limit=3000).effective(SPEC) == 3000


def test_effective_is_off_value_when_disabled() -> None:
    assert GatedState(limit=3000, enabled=False).effective(SPEC) == 0.0
```

En `tests/unit/test_types.py`: importar `EncodeError` junto a los demás errores; en
`test_enum_values_are_stable` añadir al final de la lista de roles `"export_limit"` y
`"export_enabled"` (después de `"energy_battery_discharge"`); y sustituir `DOMAIN_ERRORS` por:

```python
DOMAIN_ERRORS = {DeviceUnavailable, DeviceProtocolError, DecodeError, EncodeError, EndpointInUse}
```

En `tests/unit/test_validate.py`: ampliar los imports y añadir al final:

```python
from custom_components.modbus_solar.domain.control import GatedLimitSpec, WriteSpec  # junto a los demás imports


def gated(**changes: object) -> GatedLimitSpec:
    base = GatedLimitSpec(
        key="limit",
        switch_key="enabled",
        role=Role.EXPORT_LIMIT,
        switch_role=Role.EXPORT_ENABLED,
        write=WriteSpec(address=1000, prefix=(26, 10)),
        min_value=0,
        max_value=6000,
        step=1,
        unit="W",
        default=6000,
    )
    return replace(base, **changes)


def with_controls(*controls: GatedLimitSpec) -> DeviceProfile:
    return replace(profile(ent("a", 0)), controls=controls)


def test_valid_control() -> None:
    assert validate_profile(with_controls(gated())) == []


def test_control_keys_duplicated_with_entity_or_between_controls() -> None:
    assert validate_profile(with_controls(gated(key="a"))) == ["duplicate key: a"]
    assert validate_profile(with_controls(gated(switch_key="limit"))) == ["duplicate key: limit"]
    assert validate_profile(with_controls(gated(), gated())) == ["duplicate key: limit", "duplicate key: enabled"]


def test_control_min_above_max() -> None:
    assert "limit: min_value above max_value" in validate_profile(with_controls(gated(min_value=10, max_value=5)))


def test_control_step_must_be_positive() -> None:
    assert validate_profile(with_controls(gated(step=0))) == ["limit: step must be positive"]


def test_control_default_in_range() -> None:
    assert validate_profile(with_controls(gated(default=7000))) == ["limit: default out of range"]


def test_control_off_value_in_range() -> None:
    assert validate_profile(with_controls(gated(min_value=100))) == ["limit: off_value out of range"]


def test_control_write_scale_zero() -> None:
    write = WriteSpec(address=1000, prefix=(26, 10), scale=0)
    assert validate_profile(with_controls(gated(write=write))) == ["limit: write scale 0"]


def test_control_write_must_be_16_bit() -> None:
    write = WriteSpec(address=1000, prefix=(26, 10), dtype=DataType.U32)
    assert validate_profile(with_controls(gated(write=write))) == ["limit: write dtype u32 is not 16-bit"]


def test_control_write_must_fit_a_request() -> None:
    small = replace(with_controls(gated()), max_block_registers=2)
    assert validate_profile(small) == ["limit: write longer than max_block_registers"]


def test_control_prefix_words_are_16_bit() -> None:
    write = WriteSpec(address=1000, prefix=(26, 70000))
    assert validate_profile(with_controls(gated(write=write))) == ["limit: prefix word out of range"]


def test_control_range_must_encode() -> None:
    assert validate_profile(with_controls(gated(max_value=40000, default=40000))) == ["limit: 40000 does not encode"]
```

(El `import` de `GatedLimitSpec, WriteSpec` va con los demás imports del principio del fichero, en
orden alfabético; `ruff check` lo dirá si no.)

- [ ] **Step 2:** `bash scripts/lint.sh`, commit `test(red): export control model, encode and validation`,
  push, `bash scripts/ci-wait.sh` → rojo (`ModuleNotFoundError: …domain.control`).

- [ ] **Step 3: implementación.**

`domain/errors.py`, añadir tras `DecodeError`:

```python
class EncodeError(Exception):
    """El valor no cabe en el tipo de la escritura."""
```

`domain/types.py`: añadir al final de `Role`:

```python
    EXPORT_LIMIT = "export_limit"
    EXPORT_ENABLED = "export_enabled"
```

`domain/control.py` (nuevo):

```python
"""Controles escribibles: un límite con un interruptor que lo activa."""

from dataclasses import dataclass

from .types import DataType, Role


@dataclass(frozen=True, kw_only=True)
class WriteSpec:
    address: int  # primera dirección de la escritura
    prefix: tuple[int, ...]  # palabras fijas antes del valor: código de comando y dato 1
    dtype: DataType = DataType.S16
    scale: float = 1.0  # palabra = round(valor / scale)


@dataclass(frozen=True, kw_only=True)
class GatedLimitSpec:
    key: str  # clave del number: también translation_key y sufijo del unique_id
    switch_key: str  # clave del switch
    role: Role
    switch_role: Role
    write: WriteSpec
    min_value: float
    max_value: float
    step: float
    unit: str
    default: float  # límite inicial si no hay valor restaurado
    off_value: float = 0.0  # lo que se escribe al apagar el switch
    device_class: str | None = None  # cadena: domain no importa HA
    enabled_default: bool = True


@dataclass
class GatedState:
    """Estado en memoria de un control; lo comparten su number y su switch."""

    limit: float
    enabled: bool = True

    def effective(self, spec: GatedLimitSpec) -> float:
        # lo que el equipo debe tener: el límite si está activo, off_value si no
        return self.limit if self.enabled else spec.off_value
```

`domain/encode.py` (nuevo):

```python
"""Valor de la entidad -> palabras de 16 bits (inverso de decode)."""

import math

from .control import WriteSpec
from .errors import EncodeError


def encode(spec: WriteSpec, value: float) -> tuple[int, ...]:
    if spec.dtype.words != 1:
        raise EncodeError(f"{spec.dtype}: only 16-bit writes are supported")
    if not math.isfinite(value):
        raise EncodeError(f"value is not finite: {value}")
    raw = round(value / spec.scale)
    low, high = (-0x8000, 0x7FFF) if spec.dtype.signed else (0, 0xFFFF)
    if not low <= raw <= high:
        raise EncodeError(f"value {value} does not fit {spec.dtype}: {raw}")
    # complemento a dos de 16 bits para los negativos
    return (*spec.prefix, raw & 0xFFFF)
```

`domain/profile.py`: añadir `from .control import GatedLimitSpec` y, tras `energies`:

```python
    controls: tuple[GatedLimitSpec, ...] = ()  # parámetros escribibles del equipo
```

`domain/validate.py`: añadir imports

```python
from .control import GatedLimitSpec
from .encode import encode
from .errors import EncodeError
```

la función

```python
def _control_problems(control: GatedLimitSpec, max_block_registers: int) -> list[str]:
    problems: list[str] = []
    name = control.key
    write = control.write
    if control.min_value > control.max_value:
        problems.append(f"{name}: min_value above max_value")
    if control.step <= 0:
        problems.append(f"{name}: step must be positive")
    if not control.min_value <= control.default <= control.max_value:
        problems.append(f"{name}: default out of range")
    if not control.min_value <= control.off_value <= control.max_value:
        problems.append(f"{name}: off_value out of range")
    if write.scale == 0:
        problems.append(f"{name}: write scale 0")
    if write.dtype.words != 1:
        problems.append(f"{name}: write dtype {write.dtype} is not 16-bit")
    # el valor va detrás del prefijo en la misma petición
    if len(write.prefix) + 1 > max_block_registers:
        problems.append(f"{name}: write longer than max_block_registers")
    if any(not 0 <= word <= 0xFFFF for word in write.prefix):
        problems.append(f"{name}: prefix word out of range")
    if write.scale != 0 and write.dtype.words == 1:
        # los extremos del rango y off_value son los valores que se escribirán
        for value in (control.min_value, control.max_value, control.off_value):
            try:
                encode(write, value)
            except EncodeError:
                problems.append(f"{name}: {value} does not encode")
    return problems
```

y, en `validate_profile`, justo después del bucle de `energies`:

```python
    for control in profile.controls:
        for key in (control.key, control.switch_key):
            if key in seen:
                problems.append(f"duplicate key: {key}")
            seen.add(key)
        problems.extend(_control_problems(control, profile.max_block_registers))
```

- [ ] **Step 4:** `bash scripts/lint.sh`, commit `feat: export control model, encode and validation`, push,
  `bash scripts/ci-wait.sh` → verde.

---

### Tarea 2: puerto, casos de uso y escritura del gateway

**Files:**
- Create: `application/control.py`
- Modify: `ports/device.py`, `adapters/outbound/modbus_gateway.py`
- Test: `tests/fakes.py`, `tests/unit/test_control_usecases.py` (nuevo),
  `tests/unit/test_modbus_gateway.py`

**Interfaces:**
- Consumes: `WriteSpec`, `GatedLimitSpec`, `GatedState`, `encode`, `EncodeError` (tarea 1).
- Produces:
  - `DeviceWriter.write(spec: WriteSpec, value: float) -> None` (lanza `EncodeError`,
    `DeviceUnavailable`, `DeviceProtocolError`)
  - `set_limit(writer, spec, state, value) -> None` y `set_enabled(writer, spec, state, enabled) -> None`
  - `ModbusGateway.write(spec, value)`; `FakeWriter(error=None)` con `.writes: list[tuple[WriteSpec, float]]`

- [ ] **Step 1: tests que fallan.** En `tests/fakes.py` añadir (e importar `WriteSpec`):

```python
class FakeWriter:
    """DeviceWriter en memoria: anota (spec, valor) o lanza `error`."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.writes: list[tuple[WriteSpec, float]] = []

    async def write(self, spec: WriteSpec, value: float) -> None:
        if self.error is not None:
            raise self.error
        self.writes.append((spec, value))
```

Crear `tests/unit/test_control_usecases.py`:

```python
"""Casos de uso del límite con interruptor: escriben primero y cambian el estado después."""

import pytest

from custom_components.modbus_solar.application.control import set_enabled, set_limit
from custom_components.modbus_solar.domain.control import GatedLimitSpec, GatedState, WriteSpec
from custom_components.modbus_solar.domain.errors import DeviceUnavailable
from custom_components.modbus_solar.domain.types import Role
from tests.fakes import FakeWriter

WRITE = WriteSpec(address=1000, prefix=(26, 10))
SPEC = GatedLimitSpec(
    key="limit",
    switch_key="enabled",
    role=Role.EXPORT_LIMIT,
    switch_role=Role.EXPORT_ENABLED,
    write=WRITE,
    min_value=0,
    max_value=6000,
    step=1,
    unit="W",
    default=6000,
)


async def test_set_limit_writes_the_value_when_enabled() -> None:
    writer, state = FakeWriter(), GatedState(limit=6000)
    await set_limit(writer, SPEC, state, 3000)
    assert writer.writes == [(WRITE, 3000)]
    assert state.limit == 3000


async def test_set_limit_only_stores_when_disabled() -> None:
    writer, state = FakeWriter(), GatedState(limit=6000, enabled=False)
    await set_limit(writer, SPEC, state, 3000)
    assert writer.writes == []
    assert state.limit == 3000


@pytest.mark.parametrize("value", [-1, 6001, float("nan")])
async def test_set_limit_rejects_out_of_range(value: float) -> None:
    writer, state = FakeWriter(), GatedState(limit=6000)
    with pytest.raises(ValueError, match="limit"):
        await set_limit(writer, SPEC, state, value)
    assert (writer.writes, state.limit) == ([], 6000)


async def test_set_limit_keeps_state_when_write_fails() -> None:
    state = GatedState(limit=6000)
    with pytest.raises(DeviceUnavailable):
        await set_limit(FakeWriter(DeviceUnavailable("down")), SPEC, state, 3000)
    assert state.limit == 6000


async def test_turn_off_writes_off_value() -> None:
    writer, state = FakeWriter(), GatedState(limit=3000)
    await set_enabled(writer, SPEC, state, False)
    assert writer.writes == [(WRITE, 0.0)]
    assert state.enabled is False
    assert state.limit == 3000


async def test_turn_on_writes_the_stored_limit() -> None:
    writer, state = FakeWriter(), GatedState(limit=3000, enabled=False)
    await set_enabled(writer, SPEC, state, True)
    assert writer.writes == [(WRITE, 3000)]
    assert state.enabled is True


async def test_set_enabled_keeps_state_when_write_fails() -> None:
    state = GatedState(limit=3000)
    with pytest.raises(DeviceUnavailable):
        await set_enabled(FakeWriter(DeviceUnavailable("down")), SPEC, state, False)
    assert state.enabled is True
```

En `tests/unit/test_modbus_gateway.py`: importar `WriteEvent` (`from modbus_connection.mock import
MockModbusConnection, MockModbusUnit, ReadEvent, WriteEvent`), `EncodeError`, `WriteSpec`; añadir:

```python
GRID_POWER = WriteSpec(address=1000, prefix=(26, 0x0A))


async def test_write_is_one_fc16_request(unit: MockModbusUnit) -> None:
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    await ModbusGateway(unit, ONEPLAY).write(GRID_POWER, 3000)
    # AAA0030IMB03_N pág. 19: 01 10 03 E8 00 03 06 00 1A 00 0A 0B B8
    assert events == [WriteEvent("holding", 1000, [26, 10, 3000], 0x10)]


async def test_write_negative_value_is_twos_complement(unit: MockModbusUnit) -> None:
    await ModbusGateway(unit, ONEPLAY).write(GRID_POWER, -1)
    assert [unit.holding[1000 + i] for i in range(3)] == [26, 10, 0xFFFF]


async def test_value_that_does_not_encode_sends_nothing(unit: MockModbusUnit) -> None:
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    with pytest.raises(EncodeError):
        await ModbusGateway(unit, ONEPLAY).write(GRID_POWER, 40000)
    assert events == []


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ModbusConnectionError("refused"), DeviceUnavailable),
        (ModbusTimeoutError("timeout"), DeviceUnavailable),
        (ModbusProtocolError("bad frame"), DeviceProtocolError),
        (ModbusExceptionError(2), DeviceProtocolError),
    ],
)
async def test_translates_modbus_errors_on_write(unit: MockModbusUnit, error: Exception, expected: type[Exception]) -> None:
    unit.fail_write(1000, error)
    with pytest.raises(expected):
        await ModbusGateway(unit, ONEPLAY).write(GRID_POWER, 3000)
```

(`ruff format` ajusta la línea larga de la firma.)

- [ ] **Step 2:** `bash scripts/lint.sh`, commit `test(red): device writer, control use cases and gateway write`,
  push, `bash scripts/ci-wait.sh` → rojo (`ModuleNotFoundError: …application.control`).

- [ ] **Step 3: implementación.**

`ports/device.py` completo:

```python
"""Puertos de salida: lectura y escritura de registros de un equipo."""

from collections.abc import Mapping, Sequence
from typing import Protocol

from ..domain.control import WriteSpec
from ..domain.profile import RegisterSpec


class DeviceGateway(Protocol):
    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]:
        """Palabras crudas por registro. Lanza DeviceUnavailable o DeviceProtocolError."""
        ...


class DeviceWriter(Protocol):
    """Separado de DeviceGateway: el poller y el config flow solo leen."""

    async def write(self, spec: WriteSpec, value: float) -> None:
        """Escribe el valor ya validado. Lanza EncodeError, DeviceUnavailable o DeviceProtocolError."""
        ...
```

`application/control.py` (nuevo):

```python
"""Casos de uso de un límite con interruptor: escriben primero y cambian el estado después."""

from dataclasses import replace

from ..domain.control import GatedLimitSpec, GatedState
from ..ports.device import DeviceWriter


async def set_limit(writer: DeviceWriter, spec: GatedLimitSpec, state: GatedState, value: float) -> None:
    if not spec.min_value <= value <= spec.max_value:
        raise ValueError(f"{spec.key}: {value} outside [{spec.min_value}, {spec.max_value}]")
    # con el interruptor apagado el equipo sigue en off_value: el límite solo se guarda
    if state.enabled:
        await writer.write(spec.write, replace(state, limit=value).effective(spec))
    state.limit = value


async def set_enabled(writer: DeviceWriter, spec: GatedLimitSpec, state: GatedState, enabled: bool) -> None:
    await writer.write(spec.write, replace(state, enabled=enabled).effective(spec))
    state.enabled = enabled
```

`adapters/outbound/modbus_gateway.py`: extraer la traducción de `read` a un gestor de contexto y
añadir `write`. Imports nuevos: `from collections.abc import Iterator, Mapping, Sequence`,
`from contextlib import contextmanager`, `from ...domain.control import WriteSpec`,
`from ...domain.encode import encode`. Antes de la clase:

```python
@contextmanager
def _translated() -> Iterator[None]:
    # único sitio que conoce las excepciones de modbus_connection
    try:
        yield
    except (ModbusConnectionError, ModbusTimeoutError) as err:
        raise DeviceUnavailable(str(err)) from err
    except (ModbusExceptionError, ModbusProtocolError) as err:
        raise DeviceProtocolError(str(err)) from err
```

En `read`, sustituir el `try/except` por:

```python
            with _translated():
                values = await request(block.address, block.count)
```

y añadir a la clase:

```python
    async def write(self, spec: WriteSpec, value: float) -> None:
        words = encode(spec, value)
        # FC16 en una sola trama: código, dato 1 y valor van juntos (AAA0030IMB03_N, Nota 3)
        with _translated():
            await self._unit.write_registers(spec.address, list(words))
```

- [ ] **Step 4:** `bash scripts/lint.sh`, commit `feat: device writer and gateway write`, push,
  `bash scripts/ci-wait.sh` → verde (los tests de `read` existentes cubren la extracción).

---

### Tarea 3: control de vertido en el perfil STORAGE

**Files:**
- Modify: `profiles/ingeteam/oneplay_storage.py`
- Test: `tests/unit/test_storage_profile.py`, `tests/unit/test_profiles.py`

**Interfaces:**
- Consumes: `GatedLimitSpec`, `WriteSpec`, `Role.EXPORT_*`, `DeviceProfile.controls` (tarea 1).
- Produces: `ONEPLAY_STORAGE.controls == (GatedLimitSpec(key="export_limit", …),)`.

- [ ] **Step 1: tests que fallan.** En `tests/unit/test_storage_profile.py` añadir:

```python
def test_export_control() -> None:
    (control,) = ONEPLAY_STORAGE.controls
    assert (control.key, control.switch_key) == ("export_limit", "export_enabled")
    assert (control.role, control.switch_role) == (Role.EXPORT_LIMIT, Role.EXPORT_ENABLED)
    # AAA0030IMB03_N págs. 4, 7 y 19-20: CMD 26 (0x1A), dato 1 0x0A «Grid power», desde la dirección 1000
    assert (control.write.address, control.write.prefix, control.write.dtype) == (1000, (26, 10), DataType.S16)
    # rango del PDF [6000 W, -6000 W]: los negativos no se exponen
    assert (control.min_value, control.max_value, control.step, control.unit) == (0, 6000, 1, "W")
    assert (control.default, control.off_value, control.device_class) == (6000, 0, "power")
```

En `tests/unit/test_profiles.py` añadir:

```python
def test_oneplay_has_no_controls() -> None:
    assert ONEPLAY.controls == ()
```

- [ ] **Step 2:** `bash scripts/lint.sh`, commit `test(red): STORAGE export control`, push,
  `bash scripts/ci-wait.sh` → rojo (`ValueError: not enough values to unpack`).

- [ ] **Step 3: implementación.** En `profiles/ingeteam/oneplay_storage.py`: añadir
  `from ...domain.control import GatedLimitSpec, WriteSpec` (antes de `...domain.energy`, orden
  alfabético), el helper tras `_input` (línea 38-40):

```python
def _command(code: int, data1: int) -> WriteSpec:
    # AAA0030IMB03_N págs. 4 y 8: el comando va en los holding desde 1000 (0x03E8): código, dato 1 y
    # dato 2. Con FC16 las tres palabras van en una escritura; aquí el prefijo, y el valor es el dato 2
    return WriteSpec(address=1000, prefix=(code, data1))
```

y, tras `energies=(…)` (cierre en la línea 243, antes del `)` final del perfil):

```python
    controls=(
        GatedLimitSpec(
            key="export_limit",
            switch_key="export_enabled",
            role=Role.EXPORT_LIMIT,
            switch_role=Role.EXPORT_ENABLED,
            # CMD 26 (0x1A) «Battery Control Values», dato 1 0x0A «Grid power» (AAA0030IMB03_N págs. 7, 19-20)
            write=_command(0x1A, 0x0A),
            min_value=0,
            max_value=6000,
            step=1,
            unit="W",
            default=6000,
            device_class="power",
        ),
    ),
```

- [ ] **Step 4:** `bash scripts/lint.sh`, commit `feat: STORAGE profile declares the export control`, push,
  `bash scripts/ci-wait.sh` → verde (incluye `test_all_profiles_are_valid`, que ejecuta
  `validate_profile` sobre el control).

---

### Tarea 4: runtime y number de HA

Runtime, entidad base, number, traducciones y plataforma van acoplados (el runtime cambia de firma
y el number lo usa): un único RED y un único GREEN.

**Files:**
- Create: `adapters/inbound/entities/control.py`, `adapters/inbound/entities/number.py`, `number.py`
- Modify: `adapters/inbound/runtime.py`, `adapters/inbound/entities/base.py`,
  `adapters/inbound/entities/factory.py`, `__init__.py`, `strings.json`, `translations/en.json`,
  `translations/es.json`
- Test: `tests/ha/common.py`, `tests/ha/test_control.py` (nuevo), `tests/ha/test_coordinator.py`,
  `tests/ha/test_energy.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: `DeviceWriter` (tarea 2), `set_limit`, `GatedState`, `controls` del STORAGE (tareas 1-3).
- Produces:
  - `DeviceRuntime.writer: DeviceWriter` y `DeviceRuntime.control_states: dict[str, GatedState]`
    (clave = `GatedLimitSpec.key`)
  - `build_runtime(hass, entry, profile, gateway, writer, keys)`
  - `ModbusSolarEntity.__init__(coordinator, runtime, spec, key=None)`, con `spec: EntitySpec | EnergySpec | GatedLimitSpec`
  - `ModbusSolarControl(coordinator, runtime, spec, key)` con `_control`, `_writer`, `_state`;
    `write_errors()` (gestor de contexto → `HomeAssistantError` traducible)
  - `ModbusSolarNumber(coordinator, runtime, spec)`; `build_numbers(runtime) -> list[NumberEntity]`
  - `tests.ha.common`: `STORAGE_DATA`; `entity_id_of(hass, key, entry_id=DEVICE_ID, *, platform="sensor")`,
    `state_of(hass, key, *, platform="sensor")`

- [ ] **Step 1: tests que fallan.**

`tests/ha/common.py`: añadir tras `DEVICE_DATA`

```python
STORAGE_DATA: dict[str, Any] = {**DEVICE_DATA, "profile": "ingeteam.oneplay_storage"}
```

y generalizar las dos funciones:

```python
def entity_id_of(hass: HomeAssistant, key: str, entry_id: str = DEVICE_ID, *, platform: str = "sensor") -> str | None:
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry_id}_{key}")


def state_of(hass: HomeAssistant, key: str, *, platform: str = "sensor") -> State | None:
    entity_id = entity_id_of(hass, key, platform=platform)
    return None if entity_id is None else hass.states.get(entity_id)
```

`tests/ha/test_energy.py`: quitar la línea `STORAGE = {**DEVICE_DATA, "profile": "ingeteam.oneplay_storage"}`
y cambiar el import por `from tests.ha.common import DEVICE_ID, STORAGE_DATA as STORAGE, device_entry, entity_id_of,
setup_entry, state_of` (sin `DEVICE_DATA`, que deja de usarse).

`tests/ha/test_coordinator.py`: importar `FakeWriter` (junto a `FakeGateway`), `GatedState`, y en
`test_build_runtime_one_coordinator_per_tier_with_entities` (línea 102) y en la línea 143:

```python
    writer = FakeWriter()
    runtime = build_runtime(hass, entry, ONEPLAY, gateway, writer, ALL_KEYS)
    …
    assert runtime.writer is writer
    assert runtime.control_states == {}
```

```python
    runtime = build_runtime(hass, entry, ONEPLAY_STORAGE, FakeGateway({}), FakeWriter(), set())
    …
    assert runtime.control_states == {"export_limit": GatedState(limit=6000)}
```

(la segunda aserción va en el test de la línea 143, tras sus aserciones actuales).

`tests/unit/test_translations.py`: añadir

```python
def test_controls_and_write_error_are_translated() -> None:
    strings = load("strings.json")
    for profile in ALL_PROFILES:
        for control in profile.controls:
            assert "name" in strings["entity"]["number"][control.key], control.key
            assert "name" in strings["entity"]["switch"][control.switch_key], control.switch_key
    assert "{error}" in strings["exceptions"]["write_failed"]["message"]
```

Crear `tests/ha/test_control.py`:

```python
"""Control del vertido del STORAGE: number y switch con estado optimista y restaurado."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusConnectionError, ModbusExceptionError
from modbus_connection.mock import MockModbusUnit, WriteEvent
from pytest_homeassistant_custom_component.common import mock_restore_cache_with_extra_data

from tests.ha.common import STORAGE_DATA, device_entry, entity_id_of, setup_entry, tick

NUMBER = "number.inverter_grid_export_limit"


@pytest.fixture
def writes(storage_unit: MockModbusUnit) -> list[WriteEvent]:
    # el mock no guarda las escrituras: se recogen con on_write
    events: list[WriteEvent] = []
    storage_unit.on_write(events.append)
    return events


async def set_number(hass: HomeAssistant, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN, SERVICE_SET_VALUE, {ATTR_ENTITY_ID: NUMBER, ATTR_VALUE: value}, blocking=True
    )


def limit(hass: HomeAssistant) -> float:
    return float(hass.states.get(NUMBER).state)


async def test_storage_creates_the_number(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert entity_id_of(hass, "export_limit", platform="number") == NUMBER
    attrs = hass.states.get(NUMBER).attributes
    assert (attrs["min"], attrs["max"], attrs["step"], attrs["mode"]) == (0, 6000, 1, "box")
    assert attrs["unit_of_measurement"] == "W"
    # primer arranque: valor por defecto, sin escribir nada
    assert limit(hass) == 6000


async def test_profile_without_controls_creates_no_number(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry())
    assert hass.states.async_entity_ids("number") == []


async def test_set_number_writes_the_command(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert writes == []
    await set_number(hass, 3000)
    assert writes == [WriteEvent("holding", 1000, [26, 10, 3000], 0x10)]
    assert limit(hass) == 3000


@pytest.mark.parametrize("error", [ModbusConnectionError("no route"), ModbusExceptionError(2)])
async def test_failed_write_raises_and_keeps_the_state(
    hass: HomeAssistant,
    patch_storage_unit: MagicMock,
    storage_unit: MockModbusUnit,
    writes: list[WriteEvent],
    error: Exception,
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    storage_unit.fail_write(1000, error)
    with pytest.raises(HomeAssistantError):
        await set_number(hass, 3000)
    assert limit(hass) == 6000
    assert writes == []


async def test_number_restored_without_writing(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    mock_restore_cache_with_extra_data(
        hass, [(State(NUMBER, "2500"), {"native_value": 2500.0, "native_unit_of_measurement": "W"})]
    )
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert limit(hass) == 2500
    assert writes == []


async def test_number_unavailable_until_the_first_read(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert hass.states.get(NUMBER).state == STATE_UNAVAILABLE


async def test_number_unavailable_when_the_device_drops(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert hass.states.get(NUMBER).state != STATE_UNAVAILABLE
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    assert hass.states.get(NUMBER).state == STATE_UNAVAILABLE
```

- [ ] **Step 2:** `bash scripts/lint.sh`, commit `test(red): export limit number`, push,
  `bash scripts/ci-wait.sh` → rojo (`TypeError: build_runtime() …` y entidad `number` inexistente).

- [ ] **Step 3: implementación.**

`adapters/inbound/runtime.py`: importar `from ...domain.control import GatedState` y
`from ...ports.device import DeviceGateway, DeviceWriter`; en `DeviceRuntime`, tras `gateway` y al
final:

```python
    gateway: DeviceGateway
    writer: DeviceWriter
    coordinators: dict[PollTier, TierCoordinator]
    control_states: dict[str, GatedState]
```

`build_runtime(hass, entry, profile, gateway, writer, keys)`; en el `return DeviceRuntime(...)` añadir
`writer=writer,` y

```python
        # un estado por control, compartido por su number y su switch; sin valor restaurado manda el default
        control_states={control.key: GatedState(limit=control.default) for control in profile.controls},
```

`adapters/inbound/entities/base.py`: importar `from ....domain.control import GatedLimitSpec` y cambiar
el constructor:

```python
    def __init__(
        self,
        coordinator: TierCoordinator,
        runtime: DeviceRuntime,
        spec: EntitySpec | EnergySpec | GatedLimitSpec,
        key: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._spec = spec
        # un control da dos entidades (number y switch): la clave la elige quien construye
        key = spec.key if key is None else key
        self._attr_translation_key = key
        self._attr_unique_id = entity_unique_id(runtime.entry_id, key)
```

(el resto del constructor igual).

`adapters/inbound/entities/control.py` (nuevo):

```python
"""Base de number y switch de un control: comparten estado, escritor y traducción de errores."""

from collections.abc import Iterator
from contextlib import contextmanager

from homeassistant.exceptions import HomeAssistantError

from ....const import DOMAIN
from ....domain.control import GatedLimitSpec
from ....domain.errors import DeviceProtocolError, DeviceUnavailable, EncodeError
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


@contextmanager
def write_errors() -> Iterator[None]:
    """Traduce los errores de escritura del dominio a HomeAssistantError con mensaje traducible."""
    try:
        yield
    except (DeviceUnavailable, DeviceProtocolError, EncodeError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="write_failed", translation_placeholders={"error": str(err)}
        ) from err


class ModbusSolarControl(ModbusSolarEntity):
    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: GatedLimitSpec, key: str) -> None:
        super().__init__(coordinator, runtime, spec, key)
        self._control = spec
        self._writer = runtime.writer
        # el number y el switch del mismo control comparten el estado
        self._state = runtime.control_states[spec.key]
```

`adapters/inbound/entities/number.py` (nuevo):

```python
"""Number del límite de un control: potencia máxima que se escribe al equipo si el switch está activo."""

from homeassistant.components.number import NumberDeviceClass, NumberMode, RestoreNumber

from ....application.control import set_limit
from ....domain.control import GatedLimitSpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .control import ModbusSolarControl, write_errors


class ModbusSolarNumber(ModbusSolarControl, RestoreNumber):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: GatedLimitSpec) -> None:
        super().__init__(coordinator, runtime, spec, spec.key)
        self._attr_native_min_value = spec.min_value
        self._attr_native_max_value = spec.max_value
        self._attr_native_step = spec.step
        self._attr_native_unit_of_measurement = spec.unit
        if spec.device_class is not None:
            self._attr_device_class = NumberDeviceClass(spec.device_class)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        # el equipo no permite leer el ajuste: se recupera lo que HA mostraba y no se escribe nada
        if last is not None and isinstance(last.native_value, int | float):
            if self._control.min_value <= last.native_value <= self._control.max_value:
                self._state.limit = float(last.native_value)

    @property
    def native_value(self) -> float:
        return self._state.limit

    async def async_set_native_value(self, value: float) -> None:
        with write_errors():
            await set_limit(self._writer, self._control, self._state, value)
        self.async_write_ha_state()
```

`adapters/inbound/entities/factory.py`: importar `from homeassistant.components.number import NumberEntity`,
`from .number import ModbusSolarNumber` y añadir:

```python
def _control_coordinator(runtime: DeviceRuntime) -> TierCoordinator:
    # los controles cuelgan del tier de la entidad de prueba: si el equipo no responde, no se ofrece escribir
    probe = next(e for e in runtime.profile.entities if e.key == runtime.profile.probe_key)
    return runtime.coordinators[probe.poll]


def build_numbers(runtime: DeviceRuntime) -> list[NumberEntity]:
    coordinator = _control_coordinator(runtime)
    return [ModbusSolarNumber(coordinator, runtime, spec) for spec in runtime.profile.controls]
```

`number.py` (nuevo, en la raíz):

```python
"""Plataforma number: límites escribibles del equipo de la entry."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .adapters.inbound.entities.factory import build_numbers
from .adapters.inbound.runtime import ModbusSolarConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: ModbusSolarConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(build_numbers(entry.runtime_data))
```

`__init__.py`: `PLATFORMS = [HaPlatform.SENSOR, HaPlatform.NUMBER]` (el switch se añade en la tarea 5) y

```python
    # el mismo ModbusGateway lee y escribe: dos puertos, una implementación
    runtime = build_runtime(hass, entry, profile, gateway, gateway, keys)
```

Traducciones: con este script (ejecutarlo desde la raíz del repo con `.venv/Scripts/python`) se añaden
las claves sin reformatear el resto; comprobar con `git diff --stat` que solo hay líneas añadidas:

```python
import json
from pathlib import Path

TEXTS = {
    "strings.json": ("Grid export limit", "Grid export", "Could not write to the inverter: {error}"),
    "translations/en.json": ("Grid export limit", "Grid export", "Could not write to the inverter: {error}"),
    "translations/es.json": ("Límite de vertido a red", "Vertido a red", "No se pudo escribir en el inversor: {error}"),
}
for name, (number, switch, error) in TEXTS.items():
    path = Path("custom_components/modbus_solar") / name
    data = json.loads(path.read_text(encoding="utf-8"))
    data["entity"]["number"] = {"export_limit": {"name": number}}
    data["entity"]["switch"] = {"export_enabled": {"name": switch}}
    data["exceptions"] = {"write_failed": {"message": error}}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
```

(Las claves `entity.switch` se usan en la tarea 5; el test de traducciones de esta tarea ya las
exige.)

- [ ] **Step 4:** `bash scripts/lint.sh`, commit `feat: export limit number`, push,
  `bash scripts/ci-wait.sh` → verde.

---

### Tarea 5: switch de vertido

**Files:**
- Create: `adapters/inbound/entities/switch.py`, `switch.py`
- Modify: `adapters/inbound/entities/factory.py`, `__init__.py`
- Test: `tests/ha/test_control.py`

**Interfaces:**
- Consumes: `ModbusSolarControl`, `write_errors`, `set_enabled`, `DeviceRuntime.control_states` (tarea 4).
- Produces: `ModbusSolarSwitch(coordinator, runtime, spec)`; `build_switches(runtime) -> list[SwitchEntity]`.

- [ ] **Step 1: tests que fallan.** En `tests/ha/test_control.py`: añadir imports
  (`from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN`, `SERVICE_TURN_OFF`,
  `SERVICE_TURN_ON`, `STATE_OFF`, `STATE_ON` de `homeassistant.const`), la constante
  `SWITCH = "switch.inverter_grid_export"` y

```python
async def switch(hass: HomeAssistant, service: str) -> None:
    await hass.services.async_call(SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: SWITCH}, blocking=True)


async def test_storage_creates_the_switch(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert entity_id_of(hass, "export_enabled", platform="switch") == SWITCH
    state = hass.states.get(SWITCH)
    # primer arranque: vertido activado, sin escribir nada
    assert state.state == STATE_ON
    # no hay registro de lectura: el estado es el que HA recuerda
    assert state.attributes["assumed_state"] is True


async def test_profile_without_controls_creates_no_switch(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry())
    assert hass.states.async_entity_ids("switch") == []


async def test_switch_off_writes_zero_and_on_writes_the_limit(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    await set_number(hass, 3000)
    await switch(hass, SERVICE_TURN_OFF)
    assert hass.states.get(SWITCH).state == STATE_OFF
    # apagar el switch no cambia el valor del number
    assert limit(hass) == 3000
    await switch(hass, SERVICE_TURN_ON)
    assert hass.states.get(SWITCH).state == STATE_ON
    assert [w.values for w in writes] == [[26, 10, 3000], [26, 10, 0], [26, 10, 3000]]
    assert {(w.address, w.function_code) for w in writes} == {(1000, 0x10)}


async def test_number_with_switch_off_only_stores_the_value(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    await switch(hass, SERVICE_TURN_OFF)
    await set_number(hass, 2000)
    assert limit(hass) == 2000
    assert [w.values for w in writes] == [[26, 10, 0]]
    await switch(hass, SERVICE_TURN_ON)
    assert [w.values for w in writes] == [[26, 10, 0], [26, 10, 2000]]


@pytest.mark.parametrize("error", [ModbusConnectionError("no route"), ModbusExceptionError(2)])
async def test_failed_switch_write_raises_and_keeps_the_state(
    hass: HomeAssistant,
    patch_storage_unit: MagicMock,
    storage_unit: MockModbusUnit,
    writes: list[WriteEvent],
    error: Exception,
) -> None:
    await setup_entry(hass, device_entry(STORAGE_DATA))
    storage_unit.fail_write(1000, error)
    with pytest.raises(HomeAssistantError):
        await switch(hass, SERVICE_TURN_OFF)
    assert hass.states.get(SWITCH).state == STATE_ON
    assert writes == []


async def test_switch_and_number_restored_without_writing(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    mock_restore_cache_with_extra_data(
        hass,
        [
            (State(SWITCH, STATE_OFF), {}),
            (State(NUMBER, "2500"), {"native_value": 2500.0, "native_unit_of_measurement": "W"}),
        ],
    )
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert hass.states.get(SWITCH).state == STATE_OFF
    assert limit(hass) == 2500
    assert writes == []


async def test_switch_and_number_survive_reload(
    hass: HomeAssistant, patch_storage_unit: MagicMock, writes: list[WriteEvent]
) -> None:
    entry = device_entry(STORAGE_DATA)
    await setup_entry(hass, entry)
    await switch(hass, SERVICE_TURN_OFF)
    await set_number(hass, 2000)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(SWITCH).state == STATE_OFF
    assert limit(hass) == 2000
    # recargar no vuelve a escribir: solo está el apagado
    assert [w.values for w in writes] == [[26, 10, 0]]


async def test_switch_unavailable_until_the_first_read(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await setup_entry(hass, device_entry(STORAGE_DATA))
    assert hass.states.get(SWITCH).state == STATE_UNAVAILABLE
```

- [ ] **Step 2:** `bash scripts/lint.sh`, commit `test(red): export switch`, push,
  `bash scripts/ci-wait.sh` → rojo (`AttributeError: 'NoneType' object has no attribute 'state'`: no hay switch).

- [ ] **Step 3: implementación.**

`adapters/inbound/entities/switch.py` (nuevo):

```python
"""Switch de un control: con él activo el equipo recibe el límite; apagado, off_value."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.restore_state import RestoreEntity

from ....application.control import set_enabled
from ....domain.control import GatedLimitSpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .control import ModbusSolarControl, write_errors


class ModbusSolarSwitch(ModbusSolarControl, SwitchEntity, RestoreEntity):
    # el equipo no permite leer el ajuste: HA muestra lo último que escribió, no lo que hay
    _attr_assumed_state = True

    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: GatedLimitSpec) -> None:
        super().__init__(coordinator, runtime, spec, spec.switch_key)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        # la restauración no escribe al equipo: tras reiniciar HA el inversor conserva lo que tenía
        if last is not None and last.state in (STATE_ON, STATE_OFF):
            self._state.enabled = last.state == STATE_ON

    @property
    def is_on(self) -> bool:
        return self._state.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, enabled: bool) -> None:
        with write_errors():
            await set_enabled(self._writer, self._control, self._state, enabled)
        self.async_write_ha_state()
```

`adapters/inbound/entities/factory.py`: importar `from homeassistant.components.switch import SwitchEntity`,
`from .switch import ModbusSolarSwitch` y añadir:

```python
def build_switches(runtime: DeviceRuntime) -> list[SwitchEntity]:
    coordinator = _control_coordinator(runtime)
    return [ModbusSolarSwitch(coordinator, runtime, spec) for spec in runtime.profile.controls]
```

`switch.py` (nuevo, en la raíz): igual que `number.py` con `build_switches` y docstring
`"""Plataforma switch: interruptores de control del equipo de la entry."""`.

`__init__.py`: `PLATFORMS = [HaPlatform.SENSOR, HaPlatform.NUMBER, HaPlatform.SWITCH]`.

- [ ] **Step 4:** `bash scripts/lint.sh`, commit `feat: export switch`, push,
  `bash scripts/ci-wait.sh` → verde.

---

### Tarea 6: documentación

**Files:**
- Create: `docs/features/control.md`, `docs/decisions/0011-controls-in-profile.md`,
  `docs/decisions/0012-optimistic-restored-state.md`
- Modify: `docs/architecture/{domain,ports,application}.md`, `docs/architecture/adapters/{inbound,outbound}.md`,
  `docs/architecture/overview.md` (si lista las plataformas), `docs/README.md`,
  `docs/wiki/brands/ingeteam/README.md`, `README.md`,
  `docs/changes/2026-10-04-export-control/{spec,plan}.md` (`status: done`)

Las citas `archivo:línea` de los documentos vivos se sacan de la rama ya implementada: `graft grep
"<símbolo>"` o `grep -n`. No se copian de este plan.

- [ ] **Step 1: `docs/features/control.md`** (documento vivo, estilo de `docs/features/monitoring.md`):

```markdown
# Funcionalidad: control del vertido a red

Documento vivo. Rutas bajo `custom_components/modbus_solar/` salvo indicación. Solo el perfil
`ingeteam.oneplay_storage` declara controles; `ingeteam.oneplay` no crea ninguna entidad `number`
ni `switch`.

## Entidades

| Entidad | Plataforma | Clave | Rango | Qué hace |
|---|---|---|---|---|
| Límite de vertido a red | `number` | `export_limit` | 0-6000 W, paso 1 | Potencia máxima que el equipo inyecta a la red |
| Vertido a red | `switch` | `export_enabled` | — | ON: vertido activado. OFF: vertido desactivado |

Son independientes en pantalla: apagar el switch no cambia el valor del number.

## Qué se escribe

Una escritura FC16 de tres palabras en la dirección 1000, en una sola trama: `[26, 0x0A, W]`
(CMD 26 «Battery Control Values», dato 1 «Grid power», dato 2 = vatios; `AAA0030IMB03_N` págs. 7, 19-20).

| Acción | Palabras |
|---|---|
| Switch → ON | `[26, 10, valor del number]` |
| Switch → OFF | `[26, 10, 0]` |
| Number cambia con el switch ON | `[26, 10, valor nuevo]` |
| Number cambia con el switch OFF | no escribe; guarda el valor para el próximo ON |

0 W equivale a «no inyectar excedente a la red» (`ABH2014IQM01` apdo. 19.7.7, pág. 54).

## Estado optimista y restaurado

El equipo no tiene registro de lectura de este ajuste. HA muestra lo último que escribió y lo
restaura tras reiniciar sin escribir al equipo. Primer arranque: number a 6000 W, switch ON, sin
escritura. El switch lleva `assumed_state`.

- Si alguien cambia el vertido desde los ajustes del inversor, HA no se entera.
- El sensor extra `power_reduction_reason` (registro 30042, valor 16 «PV Surplus Injected to the Grid»)
  indica que el inversor está limitando por este motivo ahora mismo. No da el valor del ajuste.
- Las entidades nacen `unavailable` hasta la primera lectura correcta y vuelven a `unavailable` si el
  equipo cae: con el equipo sin responder no se ofrece escribir.
- Una escritura fallida lanza `HomeAssistantError` y no cambia el estado.

## Pendiente de verificar en el equipo

- Si el CMD 26 sobrevive a un reinicio del inversor (el PDF no lo dice).
- Si aplica con la batería configurada como «Lead-Acid» o «Ingeteam RS485 Protocol» únicamente (pág. 19).
- Que una escritura no solape tramas con una lectura (lo garantiza `modbus_connection`).

## Fuera de alcance

Potencia contratada y máxima potencia de consumo de red: ningún documento da registro ni comando
(`docs/wiki/brands/ingeteam/README.md`). Otros parámetros de batería: se añaden como controles nuevos.

Diseño: `docs/changes/2026-10-04-export-control/spec.md`.
```

- [ ] **Step 2: ADR `docs/decisions/0011-controls-in-profile.md`** (formato de `0009`: `status`, `date`, Contexto,
  Decisión, Consecuencias):
  - Contexto: hasta ahora solo lectura; el perfil es declarativo (ADR 0002); el STORAGE necesita escribir el
    CMD 26. Alternativas descartadas: una clase de entidad por parámetro con registros dentro del adaptador
    (la marca dejaría de ser dato del perfil); ampliar `DeviceGateway` con `write` (el poller y el flow solo leen).
  - Decisión: `GatedLimitSpec` y `WriteSpec` en `domain/control.py`, `DeviceProfile.controls`; `encode` en dominio;
    puerto `DeviceWriter` separado; `ModbusGateway` lo implementa; casos de uso `set_limit`/`set_enabled`; plataformas
    `number` y `switch` genéricas. Cita cada pieza con su `archivo:línea` real.
  - Consecuencias: otro parámetro es un `GatedLimitSpec` más o un dataclass de control nuevo; puerto, gateway,
    `WriteSpec` y `encode` no cambian; solo escrituras de 16 bits; el valor se valida en el caso de uso y en `encode`.

- [ ] **Step 3: ADR `docs/decisions/0012-optimistic-restored-state.md`**:
  - Contexto: ningún documento da un registro que lea «Grid power» (`AAA0030IMB03_N` pág. 4; `ABH2010IMB08`).
    Alternativas descartadas: leer el 30042 (solo dice si limita ahora); leer los holding 1000-1002 (la zona de
    comandos; no documentan el último valor aplicado); escribir al arrancar HA para sincronizar (cambia el equipo
    sin que el usuario lo pida).
  - Decisión: estado en memoria (`GatedState`), `RestoreNumber`/`RestoreEntity`, nunca se escribe al restaurar,
    `assumed_state` en el switch.
  - Consecuencias: cambios hechos desde el inversor no se reflejan; si aparece un registro de lectura, se añade sin
    cambiar el modelo; primer arranque = default 6000 W y ON sin escribir.

- [ ] **Step 4: documentos de arquitectura.**
  - `docs/architecture/domain.md`: secciones `control.py` (`WriteSpec`, `GatedLimitSpec`, `GatedState.effective`)
    y `encode.py` (reglas del §3.2 de la spec: `round(valor / scale)`, rango del tipo, complemento a dos, `EncodeError`
    también con `nan`/`inf` y con tipos de 32 bits); `Role` gana `export_limit` y `export_enabled`; `profile.py` gana
    `controls`; `errors.py` gana `EncodeError`; `validate.py`: las comprobaciones de controles.
  - `docs/architecture/ports.md`: `DeviceWriter` con su contrato y errores; tabla de implementaciones: `ModbusGateway`
    (lee y escribe) y `FakeWriter` (`tests/fakes.py`).
  - `docs/architecture/application.md`: `set_limit` y `set_enabled` (orden: validar, escribir, cambiar estado; un
    error deja el estado intacto).
  - `docs/architecture/adapters/outbound.md`: `write` (una trama FC16) y `_translated` compartido con `read`.
  - `docs/architecture/adapters/inbound.md`: `DeviceRuntime.writer` y `control_states`; plataformas `number` y
    `switch`; `ModbusSolarControl`, `write_errors`, `ModbusSolarNumber`, `ModbusSolarSwitch`; disponibilidad ligada
    al tier de `probe_key`; `build_numbers` y `build_switches`.
  - `docs/architecture/overview.md`: si enumera las plataformas, añadir `number` y `switch`.

- [ ] **Step 5: resto.**
  - `docs/README.md`: añadir al final de la tabla `| [2026-10-04-export-control](changes/2026-10-04-export-control/spec.md) | cerrado |`.
  - `docs/wiki/brands/ingeteam/README.md`: añadir al final de la lista de viñetas:
    «- Vertido a red del STORAGE 1Play TL M: CMD 26, dato `0x0A` «Grid power» de `AAA0030IMB03_N` (págs. 7, 19-20). La potencia contratada («Hired Grid Power», `ABH2014IQM01` pág. 54) no tiene comando ni registro Modbus documentado.»
  - `README.md` línea 10: añadir al final de la descripción del STORAGE «; switch y límite de vertido a red».
  - `docs/changes/2026-10-04-export-control/spec.md` y `plan.md`: `status: done`.

- [ ] **Step 6:** `bash scripts/lint.sh`, commit `docs: export control`, push, `bash scripts/ci-wait.sh` → verde.

---

## Auto-revisión

**Cobertura de la spec**

| Spec | Tarea |
|---|---|
| §3.1 modelo (`WriteSpec`, `GatedLimitSpec`, `controls`, roles) | 1 |
| §3.2 `encode` | 1 |
| §3.3 `GatedState` | 1 |
| §3.4 validación | 1 |
| §3.5 perfil STORAGE, `_command` | 3 |
| §4.1 `DeviceWriter` | 2 |
| §4.2 casos de uso | 2 |
| §4.3 `ModbusGateway.write` y traducción | 2 |
| §5.1 runtime y wiring | 4 |
| §5.2 plataformas, fábricas, disponibilidad, `unique_id` | 4 (number), 5 (switch) |
| §5.3 comportamiento, errores, optimista y restaurado | 4, 5 |
| §5.4 traducciones | 4 |
| §6 tests unitarios y HA | 1-5 (el solape de tramas no tiene test: spec §6) |
| §7 documentación | 6 |
| Criterios de éxito 1-6 | 1: tests de perfil válido (3); 2: switch OFF/ON (5); 3: number con switch ON/OFF (5); 4: restauración sin escritura (4, 5); 5: escritura fallida (4, 5); 6: perfil sin controles (4, 5) |

**Decisiones del plan que ajustan la spec** (ya corregidas en la spec): `Platform` no cambia (nada la
lee); `GatedLimitSpec.enabled_default` (lo lee `ModbusSolarEntity`); `EncodeError` independiente de
`DecodeError`; escrituras del mock recogidas con `on_write`; `assumed_state` en el switch.

**Tipos coherentes entre tareas:** `WriteSpec`/`GatedLimitSpec`/`GatedState`/`encode`/`EncodeError`
(1) → `DeviceWriter.write`, `set_limit`, `set_enabled`, `FakeWriter` (2) → `controls` del perfil (3) →
`DeviceRuntime.writer`, `control_states`, `build_runtime(..., writer, keys)`,
`ModbusSolarControl`, `write_errors`, `build_numbers` (4) → `ModbusSolarSwitch`, `build_switches` (5).
`control_states` se indexa por `GatedLimitSpec.key` en el runtime y en `ModbusSolarControl`.

**Sin marcadores pendientes.** Las citas `archivo:línea` de los documentos vivos se toman del código
de la rama en la tarea 6, porque no existen hasta implementar.
