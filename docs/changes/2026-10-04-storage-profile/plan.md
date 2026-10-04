---
type: feature
area: profiles
layers: [domain, application, adapters, profiles]
status: done
date: 2026-10-04
---

# Plan de implementación — Spec 1, perfil STORAGE 1Play TL M y energía calculada

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `subagent-driven-development` (recomendada) o
> `executing-plans` para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** sustituir el mapa del perfil `ingeteam.oneplay_storage` por el del INGECON SUN
STORAGE 1Play TL M (`ABH2010IMB08`) y añadir cinco contadores de energía integrados por la
integración, según `docs/changes/2026-10-04-storage-profile/spec.md`.

**Arquitectura:** el acumulador de energía y su especificación viven en `domain` (puros). El
perfil declara energías con `DeviceProfile.energies`. El adaptador de entrada crea un
`RestoreSensor` por energía que se alimenta del coordinador del tier de sus fuentes. La lectura
agrupa huecos con `DeviceProfile.max_gap` para respetar 10 registros por petición sin disparar
el número de peticiones.

**Stack:** Python 3.14, Home Assistant 2026.9.4, `modbus-connection` 4.10.0, pytest +
`pytest-homeassistant-custom-component` 0.13.367 (trae `pytest-freezer` 0.4.9), ruff,
import-linter, GitHub Actions.

## Global Constraints

- Rama de trabajo: `feat/storage-profile`, creada desde `docs/storage-profile-spec`. Nunca
  commit en `main`.
- Push a `feat/storage-profile` autorizado sin confirmar. Force push, merge, rebase y PR piden
  confirmación.
- **Tests solo en GitHub Actions.** Nunca `pytest` en la máquina Windows. RED y GREEN se
  comprueban con `bash scripts/ci-wait.sh`, lanzado con `run_in_background: true`.
- Gates locales antes de cada commit: `bash scripts/lint.sh`. Si falta `.venv`:
  `py -3.14 -m venv .venv` y `.venv/Scripts/pip install ruff import-linter`. `.venv/` no se
  commitea.
- Commits RED (`test(red): …`) permitidos en la rama. Un commit GREEN por tarea con CI en verde.
- Todo commit termina con:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5
  ```
- Comentarios del código en español. Identificadores, ficheros, logs, excepciones y
  `strings.json` en inglés.
- Dentro de `custom_components/modbus_solar` solo imports relativos.
- Contratos de import-linter intactos: `domain`, `ports`, `application` y `profiles` no
  importan `homeassistant` ni `modbus_connection`.
- STORAGE: `min_request_interval_s=1.0`, `max_block_registers=10`, `max_gap=9`, todo
  `RegisterKind.INPUT`, dirección = registro − 30001 (`ABH2010IMB08`, pág. 9).
- Identificadores estables: entidad `f"{subentry_id}_{key}"`. `inverter_state` y
  `active_power` conservan su clave.
- `graft/` y `.graft_*` nunca se commitean.
- No inventar: si una API no se comporta como dice el plan, parar y avisar con la salida real.

## Mapa de ficheros

| Fichero | Cambio | Tarea |
|---|---|---|
| `domain/profile.py` | `DeviceProfile.max_gap`, `DeviceProfile.energies` | 1, 4 |
| `application/poller.py` | `min_tier_interval` usa `profile.max_gap` | 1 |
| `adapters/outbound/modbus_gateway.py` | usa `profile.max_gap` | 1 |
| `profiles/ingeteam/oneplay.py` | nuevo: mapa viejo, id `ingeteam.oneplay` | 2 |
| `profiles/ingeteam/oneplay_storage.py` | reescrito: mapa `ABH2010IMB08` y energías | 3, 4 |
| `profiles/__init__.py` | `ALL_PROFILES = (ONEPLAY, ONEPLAY_STORAGE)` | 2, 3 |
| `domain/types.py` | roles nuevos | 3, 4 |
| `strings.json`, `translations/en.json`, `translations/es.json` | entidades nuevas | 3, 4 |
| `domain/energy.py` | nuevo: `SignFilter`, `EnergySpec`, `EnergyAccumulator` | 4 |
| `domain/validate.py` | comprobaciones de energía | 4 |
| `adapters/inbound/coordinator.py` | parámetro `always_update` | 5 |
| `adapters/inbound/runtime.py` | `enabled_keys` con fuentes; `always_update` por tier | 5 |
| `adapters/inbound/entities/base.py` | acepta `EntitySpec` o `EnergySpec` | 6 |
| `adapters/inbound/entities/energy.py` | nuevo: `ModbusSolarEnergySensor` | 6 |
| `adapters/inbound/entities/factory.py` | crea los sensores de energía | 6 |
| `tests/…` | ver cada tarea | 1-6 |
| `docs/…`, `README.md`, ADR 0009 | documentación | 7 |

Rutas de código relativas a `custom_components/modbus_solar/`.

---

### Tarea 1: `max_gap` en el perfil

**Files:**
- Modify: `domain/profile.py:34-45`, `application/poller.py:46-49`,
  `adapters/outbound/modbus_gateway.py:19-29`
- Test: `tests/unit/test_poller.py`, `tests/unit/test_modbus_gateway.py`

**Interfaces:**
- Produces: `DeviceProfile.max_gap: int = 0`; `min_tier_interval(profile, tier) -> float`;
  `ModbusGateway(unit, profile)`. Ninguno de los dos acepta ya `max_gap` como argumento.

- [ ] **Step 1: tests que fallan**

`tests/unit/test_modbus_gateway.py`, sustituir `test_max_gap_reads_through_gaps`:

```python
async def test_max_gap_reads_through_gaps(unit: MockModbusUnit) -> None:
    specs = [RegisterSpec(address=10, dtype=DataType.U16), RegisterSpec(address=13, dtype=DataType.U16)]
    await ModbusGateway(unit, replace(ONEPLAY_STORAGE, max_gap=2)).read(specs)
    assert unit.read_events == [ReadEvent("holding", 10, 4)]
```

(con `from dataclasses import replace`). `tests/unit/test_poller.py`, añadir:

```python
def test_min_tier_interval_uses_profile_max_gap() -> None:
    # 0x101D y 0x1037 quedan a 25 registros: con max_gap=25 se leen en un bloque
    assert min_tier_interval(replace(ONEPLAY_STORAGE, max_gap=25), PollTier.FAST) == 1.0
```

- [ ] **Step 2:** `bash scripts/lint.sh`, commit `test(red): max_gap from profile`,
  `bash scripts/ci-wait.sh` → rojo con `TypeError: ... unexpected keyword argument 'max_gap'`.

- [ ] **Step 3: implementación**

`domain/profile.py`, en `DeviceProfile` tras `max_block_registers`:

```python
    max_gap: int = 0  # huecos de hasta max_gap registros se leen dentro del mismo bloque
```

`application/poller.py`:

```python
def min_tier_interval(profile: DeviceProfile, tier: PollTier) -> float:
    """Segundos mínimos para leer el tier entero respetando el espaciado entre peticiones."""
    registers = [e.register for e in profile.entities if e.poll is tier]
    return len(plan_blocks(registers, profile.max_gap, profile.max_block_registers)) * profile.min_request_interval_s
```

`adapters/outbound/modbus_gateway.py`:

```python
    def __init__(self, unit: ModbusUnit, profile: DeviceProfile) -> None:
        self._unit = unit
        self._max_gap = profile.max_gap
        self._max_count = profile.max_block_registers
```

- [ ] **Step 4:** lint, commit `feat: max_gap in DeviceProfile`, `ci-wait.sh` → verde.

---

### Tarea 2: el mapa viejo pasa a `ingeteam.oneplay`

**Files:**
- Create: `profiles/ingeteam/oneplay.py` (contenido actual de `oneplay_storage.py`)
- Modify: `profiles/__init__.py`, `profiles/ingeteam/oneplay_storage.py` (se borra en esta
  tarea y se recrea en la 3)
- Test: todos los que importan `ONEPLAY_STORAGE` o usan `"ingeteam.oneplay_storage"`:
  `tests/fakes.py`, `tests/ha/common.py`, `tests/ha/conftest.py`, `tests/ha/test_*.py`,
  `tests/unit/test_profiles.py`, `test_poller.py`, `test_probe.py`, `test_modbus_gateway.py`

**Interfaces:**
- Produces: `profiles.ingeteam.oneplay.ONEPLAY` con `id="ingeteam.oneplay"`,
  `models=("1Play TL M",)`; registros, claves y enum sin cambios.

- [ ] **Step 1: tests que fallan.** En los tests listados:
  - `from custom_components.modbus_solar.profiles.ingeteam.oneplay import ONEPLAY` y
    `ONEPLAY_STORAGE` → `ONEPLAY`;
  - `"ingeteam.oneplay_storage"` → `"ingeteam.oneplay"` (`DEVICE_DATA`, `USER_INPUT`,
    diagnostics, catálogo, duplicados);
  - modelo `"1Play Storage"` → `"1Play TL M"` (`test_profiles.py`, `test_init.py`);
  - docstrings: «1Play Storage» → «1Play TL M (sin storage)».
- [ ] **Step 2:** lint, commit `test(red): old map as ingeteam.oneplay`, CI → rojo con
  `ModuleNotFoundError: ...profiles.ingeteam.oneplay`.
- [ ] **Step 3: implementación.** `git mv profiles/ingeteam/oneplay_storage.py
  profiles/ingeteam/oneplay.py` y cambiar:

```python
"""INGECON SUN 1Play TL M, sin storage. Fuente: PDF ACL2010IMB05 (docs/wiki/brands/ingeteam/1-play-tl-m/)."""
...
ONEPLAY = DeviceProfile(
    id="ingeteam.oneplay",
    brand="ingeteam",
    device_type="inverter",
    models=("1Play TL M",),
```

`profiles/__init__.py`:

```python
from .ingeteam.oneplay import ONEPLAY

ALL_PROFILES: tuple[DeviceProfile, ...] = (ONEPLAY,)
```

- [ ] **Step 4:** lint, commit `refactor: old ACL2010IMB05 map becomes ingeteam.oneplay`, CI → verde.

---

### Tarea 3: perfil STORAGE

**Files:**
- Create: `profiles/ingeteam/oneplay_storage.py`, `tests/unit/test_storage_profile.py`
- Modify: `domain/types.py:33-38`, `profiles/__init__.py`, `strings.json`,
  `translations/en.json`, `translations/es.json`, `tests/unit/test_translations.py`,
  `tests/unit/test_profiles.py` (catálogo), `tests/unit/test_types.py` (valores de `Role`)

**Interfaces:**
- Consumes: `DeviceProfile.max_gap` (Tarea 1).
- Produces: `profiles.ingeteam.oneplay_storage.ONEPLAY_STORAGE`; roles `Role.PV_VOLTAGE`,
  `PV_CURRENT`, `PV_POWER`, `BATTERY_VOLTAGE`, `BATTERY_CURRENT`, `BATTERY_POWER`,
  `BATTERY_SOC`, `BATTERY_SOH`, `BATTERY_STATE`, `BATTERY_TEMPERATURE`, `GRID_VOLTAGE`,
  `GRID_FREQUENCY`, `GRID_POWER`, `LOAD_POWER`, `DIAGNOSTIC`.
  `ALL_PROFILES = (ONEPLAY, ONEPLAY_STORAGE)`. El orden no decide el perfil por defecto del
  formulario: `Catalog.for_brand` ordena por `id` (`application/catalog.py:19-20`) y el flow usa
  `profiles[0]` (`adapters/inbound/flow.py:103`), que es `ingeteam.oneplay`.

- [ ] **Step 1: tests que fallan.** `tests/unit/test_storage_profile.py`:

```python
"""Perfil INGECON SUN STORAGE 1Play TL M (ABH2010IMB08)."""

import pytest

from custom_components.modbus_solar.application.poller import min_tier_interval
from custom_components.modbus_solar.domain.blocks import plan_blocks
from custom_components.modbus_solar.domain.types import DataType, PollTier, RegisterKind, Role
from custom_components.modbus_solar.domain.validate import validate_profile
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE

CORE = [
    "inverter_state", "active_power", "pv1_voltage", "pv1_current", "pv1_power", "pv2_voltage",
    "pv2_current", "pv2_power", "battery_voltage", "battery_current", "battery_power", "battery_soc",
    "battery_soh", "battery_state", "battery_temperature", "grid_voltage", "grid_frequency",
    "grid_power", "load_power",
]
EXTRA = [
    "operation_time", "battery_discharge_limit_reason", "battery_charge_limit_reason", "reactive_power",
    "power_factor", "power_reduction_ratio", "power_reduction_reason", "critical_load_voltage",
    "critical_load_current", "critical_load_frequency", "critical_load_power", "internal_meter_voltage",
    "internal_meter_current", "internal_meter_frequency", "internal_meter_power", "dc_bus_voltage",
    "inverter_temperature", "isolation_positive", "isolation_negative", "external_pv_power",
    "ev_charger_power",
]


def entity(key: str):
    return next(e for e in ONEPLAY_STORAGE.entities if e.key == key)


def test_identity_and_limits() -> None:
    p = ONEPLAY_STORAGE
    assert (p.id, p.brand, p.device_type, p.models) == (
        "ingeteam.oneplay_storage", "ingeteam", "inverter", ("STORAGE 1Play TL M",),
    )
    # ABH2014IQM01 apdo. 19.6.1 (pág. 50): >= 1 s entre peticiones y <= 10 registros por petición
    assert (p.min_request_interval_s, p.max_block_registers, p.max_gap) == (1.0, 10, 9)
    assert (p.default_port, p.default_unit_id, p.probe_key) == (502, 1, "inverter_state")
    assert validate_profile(p) == []


def test_core_enabled_and_extra_disabled() -> None:
    assert [e.key for e in ONEPLAY_STORAGE.entities] == CORE + EXTRA
    for key in CORE:
        assert entity(key).enabled_default, key
        assert entity(key).entity_category is None, key
    for key in EXTRA:
        e = entity(key)
        assert (e.enabled_default, e.poll, e.entity_category, e.role) == (
            False, PollTier.SLOW, "diagnostic", Role.DIAGNOSTIC,
        ), key


def test_all_registers_are_input() -> None:
    for e in ONEPLAY_STORAGE.entities:
        assert e.register.kind is RegisterKind.INPUT, e.key


@pytest.mark.parametrize(
    ("key", "address", "dtype", "scale", "unit", "poll"),
    [
        ("inverter_state", 15, DataType.U16, 1.0, None, PollTier.FAST),
        ("active_power", 37, DataType.S16, 1.0, "W", PollTier.FAST),
        ("pv1_current", 32, DataType.U16, 0.01, "A", PollTier.NORMAL),
        ("battery_voltage", 17, DataType.U16, 0.1, "V", PollTier.NORMAL),
        ("battery_power", 19, DataType.S16, 1.0, "W", PollTier.FAST),
        ("battery_temperature", 27, DataType.S16, 0.1, "°C", PollTier.SLOW),
        ("grid_frequency", 70, DataType.U16, 0.1, "Hz", PollTier.NORMAL),
        ("grid_power", 71, DataType.S16, 1.0, "W", PollTier.FAST),
        ("load_power", 78, DataType.U16, 1.0, "W", PollTier.FAST),
        ("operation_time", 6, DataType.U32, 1.0, "h", PollTier.SLOW),
        ("power_factor", 39, DataType.S16, 0.001, None, PollTier.SLOW),
        ("ev_charger_power", 80, DataType.S16, 1.0, "W", PollTier.SLOW),
    ],
)
def test_sample_registers_match_pdf(
    key: str, address: int, dtype: DataType, scale: float, unit: str | None, poll: PollTier
) -> None:
    e = entity(key)
    assert (e.register.address, e.register.dtype, e.register.scale, e.unit, e.poll) == (
        address, dtype, scale, unit, poll,
    )


@pytest.mark.parametrize(
    ("key", "device_class", "state_class"),
    [
        ("inverter_state", "enum", None),
        ("battery_soc", "battery", "measurement"),
        ("battery_soh", None, "measurement"),
        ("operation_time", "duration", "total_increasing"),
        ("reactive_power", "reactive_power", "measurement"),
        ("power_factor", None, "measurement"),
        ("power_reduction_reason", None, None),
    ],
)
def test_classes(key: str, device_class: str | None, state_class: str | None) -> None:
    assert (entity(key).device_class, entity(key).state_class) == (device_class, state_class)


def test_enums() -> None:
    assert list(entity("inverter_state").enum.values()) == [
        "stopped", "starting", "off_grid", "on_grid", "on_grid_battery_standby", "waiting_to_connect",
        "critical_loads_bypassed", "emergency_charge_pv", "emergency_charge_grid", "locked_waiting_reset",
        "error",
    ]
    assert list(entity("battery_state").enum.values()) == [
        "standby", "discharging", "charging_constant_current", "charging_constant_voltage", "floating",
        "equalizing", "bms_communication_error", "not_configured", "calibration_step_1",
        "calibration_step_2", "standby_manual",
    ]
    assert list(entity("inverter_state").enum) == list(range(11))
    assert list(entity("battery_state").enum) == list(range(11))


@pytest.mark.parametrize("tier", list(PollTier))
def test_no_block_over_ten_registers(tier: PollTier) -> None:
    registers = [e.register for e in ONEPLAY_STORAGE.entities if e.poll is tier]
    for block in plan_blocks(registers, ONEPLAY_STORAGE.max_gap, ONEPLAY_STORAGE.max_block_registers):
        assert block.count <= 10


@pytest.mark.parametrize(("tier", "expected"), [(PollTier.FAST, 3.0), (PollTier.NORMAL, 3.0)])
def test_tiers_fit_default_intervals(tier: PollTier, expected: float) -> None:
    # fast: bloques 15-20, 33-37 y 71-78; normal: 17-26, 31-35 y 69-70 (spec §3.1)
    assert min_tier_interval(ONEPLAY_STORAGE, tier) == expected
```

`tests/unit/test_translations.py`, sustituir `test_every_entity_and_enum_state_is_translated`:

```python
def test_every_entity_and_enum_state_is_translated() -> None:
    sensors = load("strings.json")["entity"]["sensor"]
    options: dict[str, set[str]] = {}
    for profile in ALL_PROFILES:
        for spec in profile.entities:
            assert "name" in sensors[spec.key], spec.key
            if spec.enum is not None:
                options.setdefault(spec.key, set()).update(spec.enum.values())
    # la clave es translation_key en todos los perfiles: state lleva la unión de sus opciones
    for key, values in options.items():
        assert set(sensors[key]["state"]) == values, key
```

`tests/unit/test_profiles.py`, `test_catalog_lookup`:

```python
    assert CATALOG.for_brand("ingeteam") == [ONEPLAY, ONEPLAY_STORAGE]
    assert CATALOG.get("ingeteam.oneplay_storage") is ONEPLAY_STORAGE
```

- [ ] **Step 2:** lint, commit `test(red): STORAGE 1Play TL M profile`, CI → rojo con
  `ModuleNotFoundError: ...oneplay_storage`.

- [ ] **Step 3: implementación.** `domain/types.py`, en `Role`:

```python
    PV_VOLTAGE = "pv_voltage"
    PV_CURRENT = "pv_current"
    PV_POWER = "pv_power"
    BATTERY_VOLTAGE = "battery_voltage"
    BATTERY_CURRENT = "battery_current"
    BATTERY_POWER = "battery_power"
    BATTERY_SOC = "battery_soc"
    BATTERY_SOH = "battery_soh"
    BATTERY_STATE = "battery_state"
    BATTERY_TEMPERATURE = "battery_temperature"
    GRID_VOLTAGE = "grid_voltage"
    GRID_FREQUENCY = "grid_frequency"
    GRID_POWER = "grid_power"
    LOAD_POWER = "load_power"
    DIAGNOSTIC = "diagnostic"  # entidades extra sin significado común entre marcas
```

`profiles/ingeteam/oneplay_storage.py`: helpers `_input(register, dtype, scale)` (resta
30001), `_core(...)` y `_extra(...)`; enums `INVERTER_STATES` y `BATTERY_STATES` de §3.4;
entidades de §3.2 y §3.3 en ese orden. Clases y unidades:

| Clave | `device_class` | `state_class` | `unit` |
|---|---|---|---|
| potencias (`*_power`) | `power` | `measurement` | `W` |
| tensiones (`*_voltage`) | `voltage` | `measurement` | `V` |
| corrientes (`*_current`) | `current` | `measurement` | `A` |
| frecuencias (`*_frequency`) | `frequency` | `measurement` | `Hz` |
| temperaturas | `temperature` | `measurement` | `°C` |
| `battery_soc` | `battery` | `measurement` | `%` |
| `battery_soh`, `power_reduction_ratio` | — | `measurement` | `%` |
| `reactive_power` | `reactive_power` | `measurement` | `var` |
| `power_factor` | — | `measurement` | — |
| `isolation_*` | — | `measurement` | `kΩ` |
| `operation_time` | `duration` | `total_increasing` | `h` |
| enums | `enum` | — | — |
| `*_reason` | — | — | — |

`profiles/__init__.py`:

```python
from .ingeteam.oneplay import ONEPLAY
from .ingeteam.oneplay_storage import ONEPLAY_STORAGE

ALL_PROFILES: tuple[DeviceProfile, ...] = (ONEPLAY, ONEPLAY_STORAGE)
```

`strings.json` y `en.json` (copia literal), `entity.sensor`: nombre de cada clave nueva;
`inverter_state.state` con la unión de los 3 estados viejos y los 11 nuevos; `battery_state.state`
con sus 11. `es.json` con las mismas claves en español.

`tests/unit/test_types.py`: `test_enum_values_are_stable` fija la lista completa de `Role`; se
amplía con los roles nuevos en el mismo orden que `domain/types.py`.

- [ ] **Step 4:** lint, commit `feat: STORAGE 1Play TL M profile (ABH2010IMB08)`, CI → verde.

---

### Tarea 4: modelo de energía en `domain`, validación y energías del STORAGE

**Files:**
- Create: `domain/energy.py`, `tests/unit/test_energy.py`
- Modify: `domain/types.py` (roles de energía), `domain/profile.py` (`energies`),
  `domain/validate.py`, `profiles/ingeteam/oneplay_storage.py`, `strings.json`, `en.json`,
  `es.json`, `tests/unit/test_validate.py`, `tests/unit/test_storage_profile.py`,
  `tests/unit/test_translations.py`

**Interfaces:**
- Produces:
  - `SignFilter(StrEnum)`: `POSITIVE = "positive"`, `NEGATIVE = "negative"`.
  - `EnergySpec(key: str, role: Role, sources: tuple[str, ...], sign: SignFilter, enabled_default: bool = True)`, frozen, kw_only.
  - `EnergyAccumulator(sign: SignFilter, max_gap_s: float, total_kwh: float = 0.0)`;
    `add(t: float, power_w: float | None) -> None`; propiedad `total_kwh -> float`.
  - `DeviceProfile.energies: tuple[EnergySpec, ...] = ()`.
  - Roles `ENERGY_SOLAR`, `ENERGY_GRID_IMPORT`, `ENERGY_GRID_EXPORT`, `ENERGY_BATTERY_CHARGE`,
    `ENERGY_BATTERY_DISCHARGE`.
  - Mensajes de `validate_profile`: `duplicate key: <k>`, `<k>: unknown source <s>`,
    `<k>: source <s> is not power`, `<k>: sources in different tiers`.

- [ ] **Step 1: tests que fallan.** `tests/unit/test_energy.py`:

```python
"""EnergyAccumulator: trapecio sobre potencia filtrada por signo."""

import pytest

from custom_components.modbus_solar.domain.energy import EnergyAccumulator, SignFilter


def run(acc: EnergyAccumulator, *samples: tuple[float, float | None]) -> float:
    for t, power in samples:
        acc.add(t, power)
    return acc.total_kwh


def test_trapezoid() -> None:
    assert run(EnergyAccumulator(SignFilter.POSITIVE, 7200), (0, 1000), (3600, 3000)) == pytest.approx(2.0)


def test_positive_filter_ignores_negative_power() -> None:
    assert run(EnergyAccumulator(SignFilter.POSITIVE, 60), (0, -500), (10, -500)) == 0


def test_negative_filter_integrates_absolute_value() -> None:
    assert run(EnergyAccumulator(SignFilter.NEGATIVE, 7200), (0, -1800), (3600, -1800)) == pytest.approx(1.8)
    assert run(EnergyAccumulator(SignFilter.NEGATIVE, 60), (0, 500), (10, 500)) == 0


def test_none_breaks_the_series() -> None:
    acc = EnergyAccumulator(SignFilter.POSITIVE, 60)
    assert run(acc, (0, 3600), (10, None), (20, 3600)) == 0
    assert run(acc, (30, 3600)) == pytest.approx(0.01)


def test_gap_over_max_is_not_integrated() -> None:
    acc = EnergyAccumulator(SignFilter.POSITIVE, 15)
    assert run(acc, (0, 3600), (20, 3600)) == 0
    assert run(acc, (30, 3600)) == pytest.approx(0.01)


def test_time_going_backwards_is_not_integrated() -> None:
    assert run(EnergyAccumulator(SignFilter.POSITIVE, 60), (10, 3600), (5, 3600)) == 0


def test_restored_total_is_kept_and_never_negative() -> None:
    acc = EnergyAccumulator(SignFilter.POSITIVE, 60, total_kwh=1.5)
    assert run(acc, (0, 3600), (10, 3600)) == pytest.approx(1.51)
    assert EnergyAccumulator(SignFilter.POSITIVE, 60, total_kwh=-1).total_kwh == 0


def test_total_never_decreases() -> None:
    acc = EnergyAccumulator(SignFilter.POSITIVE, 60)
    totals = [run(acc, (t, p)) for t, p in [(0, 500), (5, -800), (10, 1200), (15, None), (20, -50), (25, 300)]]
    assert totals == sorted(totals)
```

`tests/unit/test_validate.py`, añadir (con `replace`, `EnergySpec`, `SignFilter`):

```python
def power(key: str, address: int, poll: PollTier = PollTier.FAST, device_class: str | None = "power") -> EntitySpec:
    return replace(ent(key, address, device_class=device_class), poll=poll)


def energy(key: str = "e", *sources: str) -> EnergySpec:
    return EnergySpec(key=key, role=Role.ENERGY_SOLAR, sources=sources or ("a",), sign=SignFilter.POSITIVE)


def with_energies(*energies: EnergySpec, entities: tuple[EntitySpec, ...] | None = None) -> DeviceProfile:
    return replace(profile(*(entities or (power("a", 0), power("b", 1)))), energies=energies)


def test_valid_energy() -> None:
    assert validate_profile(with_energies(energy("e", "a", "b"))) == []


def test_energy_key_duplicated_with_entity_or_energy() -> None:
    assert validate_profile(with_energies(energy("a"))) == ["duplicate key: a"]
    assert validate_profile(with_energies(energy("e"), energy("e"))) == ["duplicate key: e"]


def test_energy_unknown_source() -> None:
    assert validate_profile(with_energies(energy("e", "z"))) == ["e: unknown source z"]


def test_energy_source_must_be_power() -> None:
    entities = (power("a", 0), power("b", 1, device_class="voltage"))
    assert validate_profile(with_energies(energy("e", "b"), entities=entities)) == ["e: source b is not power"]


def test_energy_sources_in_one_tier() -> None:
    entities = (power("a", 0), power("b", 1, poll=PollTier.NORMAL))
    assert validate_profile(with_energies(energy("e", "a", "b"), entities=entities)) == [
        "e: sources in different tiers"
    ]
```

`tests/unit/test_storage_profile.py`, añadir:

```python
def test_energies() -> None:
    assert [(e.key, e.role, e.sources, e.sign, e.enabled_default) for e in ONEPLAY_STORAGE.energies] == [
        ("solar_energy", Role.ENERGY_SOLAR, ("pv1_power", "pv2_power"), SignFilter.POSITIVE, True),
        ("grid_import_energy", Role.ENERGY_GRID_IMPORT, ("grid_power",), SignFilter.POSITIVE, True),
        ("grid_export_energy", Role.ENERGY_GRID_EXPORT, ("grid_power",), SignFilter.NEGATIVE, True),
        ("battery_charge_energy", Role.ENERGY_BATTERY_CHARGE, ("battery_power",), SignFilter.NEGATIVE, True),
        ("battery_discharge_energy", Role.ENERGY_BATTERY_DISCHARGE, ("battery_power",), SignFilter.POSITIVE, True),
    ]
```

`tests/unit/test_translations.py`, en el bucle por perfil:

```python
        for energy in profile.energies:
            assert "name" in sensors[energy.key], energy.key
```

- [ ] **Step 2:** lint, commit `test(red): energy model and validation`, CI → rojo con
  `ModuleNotFoundError: ...domain.energy`.

- [ ] **Step 3: implementación.** `domain/energy.py`:

```python
"""Energía calculada: integra la potencia leída cuando el equipo no da contadores."""

from dataclasses import dataclass
from enum import StrEnum

from .types import Role


class SignFilter(StrEnum):
    """Parte de la potencia que cuenta: la positiva, o la negativa en valor absoluto."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass(frozen=True, kw_only=True)
class EnergySpec:
    key: str  # también translation_key y sufijo del unique_id
    role: Role
    sources: tuple[str, ...]  # claves de entidades de potencia (W); se suman
    sign: SignFilter
    enabled_default: bool = True


class EnergyAccumulator:
    """Acumula kWh por la regla del trapecio sobre la potencia filtrada."""

    def __init__(self, sign: SignFilter, max_gap_s: float, total_kwh: float = 0.0) -> None:
        self._sign = sign
        self._max_gap_s = max_gap_s
        self._total_kwh = max(total_kwh, 0.0)
        self._last: tuple[float, float] | None = None

    @property
    def total_kwh(self) -> float:
        return self._total_kwh

    def add(self, t: float, power_w: float | None) -> None:
        if power_w is None:
            # sin valor: el tramo que contiene esta muestra no se integra
            self._last = None
            return
        filtered = max(power_w, 0.0) if self._sign is SignFilter.POSITIVE else max(-power_w, 0.0)
        if self._last is not None:
            last_t, last_w = self._last
            elapsed = t - last_t
            # un hueco largo (HA parado, tier sin leer) no se integra
            if 0 < elapsed <= self._max_gap_s:
                self._total_kwh += (last_w + filtered) / 2 * elapsed / 3_600_000
        self._last = (t, filtered)
```

`domain/types.py`, en `Role`:

```python
    ENERGY_SOLAR = "energy_solar"
    ENERGY_GRID_IMPORT = "energy_grid_import"
    ENERGY_GRID_EXPORT = "energy_grid_export"
    ENERGY_BATTERY_CHARGE = "energy_battery_charge"
    ENERGY_BATTERY_DISCHARGE = "energy_battery_discharge"
```

`domain/profile.py`: `from .energy import EnergySpec` y, al final de `DeviceProfile`:

```python
    energies: tuple[EnergySpec, ...] = ()  # contadores calculados por la integración
```

`domain/validate.py`, tras la comprobación de `probe_key`:

```python
    by_key = {spec.key: spec for spec in profile.entities}
    for energy in profile.energies:
        if energy.key in seen:
            problems.append(f"duplicate key: {energy.key}")
        seen.add(energy.key)
        sources = [by_key.get(key) for key in energy.sources]
        for key, source in zip(energy.sources, sources, strict=True):
            if source is None:
                problems.append(f"{energy.key}: unknown source {key}")
            elif source.device_class != "power":
                problems.append(f"{energy.key}: source {key} is not power")
        # el sensor de energía se suscribe a un solo coordinador
        if len({source.poll for source in sources if source is not None}) > 1:
            problems.append(f"{energy.key}: sources in different tiers")
```

`profiles/ingeteam/oneplay_storage.py`: `energies=(...)` con la tabla de §4.1 (signos
supuestos de §3.5 en un comentario). Traducciones: nombre de las cinco energías.

- [ ] **Step 4:** lint, commit `feat: computed energy model and STORAGE energies`, CI → verde.

---

### Tarea 5: qué se lee y cuándo se avisa

**Files:**
- Modify: `adapters/inbound/coordinator.py:22-42`, `adapters/inbound/runtime.py:35-70`
- Test: `tests/ha/test_coordinator.py`

**Interfaces:**
- Consumes: `DeviceProfile.energies`, `EnergySpec.sources` (Tarea 4).
- Produces: `TierCoordinator(..., always_update: bool = False)`; `enabled_keys` incluye las
  fuentes de cada energía habilitada; `build_runtime` pasa `always_update=True` a los tiers
  con fuentes de energía.

- [ ] **Step 1: tests que fallan.** `tests/ha/test_coordinator.py`:

```python
async def test_energy_sources_are_read_with_power_sensor_disabled(hass: HomeAssistant) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    for key in ("pv1_power", "solar_energy"):
        registry.async_get_or_create(
            "sensor", DOMAIN, f"{DEVICE_ID}_{key}", config_entry=entry, config_subentry_id=DEVICE_ID,
            disabled_by=er.RegistryEntryDisabler.USER if key == "pv1_power" else None,
        )
    assert "pv1_power" in enabled_keys(registry, DEVICE_ID, ONEPLAY_STORAGE)
    registry.async_update_entity(
        registry.async_get_entity_id("sensor", DOMAIN, f"{DEVICE_ID}_solar_energy"),
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    assert "pv1_power" not in enabled_keys(registry, DEVICE_ID, ONEPLAY_STORAGE)


async def test_tiers_with_energy_sources_always_update(hass: HomeAssistant) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    runtime = build_runtime(hass, entry, entry.subentries[DEVICE_ID], ONEPLAY_STORAGE, FakeGateway({}), set())
    assert {tier: c.always_update for tier, c in runtime.coordinators.items()} == {
        PollTier.FAST: True, PollTier.NORMAL: False, PollTier.SLOW: False,
    }
```

(con `from ...profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE`). En
`test_build_runtime_one_coordinator_per_tier_with_entities`, añadir
`assert not runtime.coordinators[PollTier.FAST].always_update` (el perfil viejo no tiene energías).

- [ ] **Step 2:** lint, commit `test(red): energy sources read and always_update`, CI → rojo.

- [ ] **Step 3: implementación.** `coordinator.py`: parámetro `always_update: bool = False`
  tras `keys`, pasado a `super().__init__` con el comentario:

```python
            # False: HA solo escribe estado si el TierResult cambia. Los tiers con fuentes de
            # energía van con True: el acumulador necesita cada muestra aunque no cambie
            always_update=always_update,
```

`runtime.py`:

```python
def _is_enabled(registry: er.EntityRegistry, platform: str, subentry_id: str, key: str, default: bool) -> bool:
    entity_id = registry.async_get_entity_id(platform, DOMAIN, entity_unique_id(subentry_id, key))
    if entity_id is None:
        # entidad aún no registrada: manda el valor por defecto del perfil
        return default
    entity = registry.async_get(entity_id)
    return entity is not None and entity.disabled_by is None


def enabled_keys(registry: er.EntityRegistry, subentry_id: str, profile: DeviceProfile) -> frozenset[str]:
    keys = {
        spec.key
        for spec in profile.entities
        if _is_enabled(registry, spec.platform, subentry_id, spec.key, spec.enabled_default)
    }
    for energy in profile.energies:
        # una energía habilitada necesita sus fuentes aunque su sensor de potencia esté deshabilitado
        if _is_enabled(registry, Platform.SENSOR, subentry_id, energy.key, energy.enabled_default):
            keys.update(energy.sources)
    return frozenset(keys)
```

y en `build_runtime`:

```python
    by_key = {spec.key: spec for spec in profile.entities}
    energy_tiers = {by_key[key].poll for energy in profile.energies for key in energy.sources}
    ...
            always_update=tier in energy_tiers,
```

- [ ] **Step 4:** lint, commit `feat: read energy sources and always update their tier`, CI → verde.

---

### Tarea 6: sensor de energía en HA

**Files:**
- Create: `adapters/inbound/entities/energy.py`, `tests/ha/test_energy.py`
- Modify: `adapters/inbound/entities/base.py`, `adapters/inbound/entities/factory.py`,
  `tests/ha/conftest.py` (fixture `storage_unit`)

**Interfaces:**
- Consumes: `EnergyAccumulator`, `EnergySpec` (Tarea 4); `always_update` (Tarea 5).
- Produces: `ModbusSolarEnergySensor(coordinator, runtime, spec: EnergySpec, brand_device_id)`;
  `build_sensors` devuelve también un sensor por energía.

- [ ] **Step 1: tests que fallan.** `tests/ha/conftest.py`:

```python
# palabras crudas del STORAGE por dirección (registro - 30001); el mock devuelve 0 en el resto
STORAGE_INPUT = {15: 3, 19: 500, 20: 80, 33: 2000, 36: 1000, 37: 2500, 71: 0x10000 - 300, 78: 2200}


@pytest.fixture
def storage_unit() -> MockModbusUnit:
    # on_grid; batería descarga 500 W; FV 2000 + 1000 W; red exporta 300 W
    unit = MockModbusConnection().for_unit(1)
    unit.input.update(STORAGE_INPUT)
    return unit


@pytest.fixture
def patch_storage_unit(storage_unit: MockModbusUnit) -> Generator[MagicMock]:
    with patch("custom_components.modbus_solar.async_get_unit", return_value=storage_unit) as mock:
        yield mock
```

`tests/ha/test_energy.py`:

```python
"""Sensores de energía calculada del STORAGE: crecen, se cortan con fallos y se restauran."""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE_DATA, DEVICE_ID, brand_entry, entity_id_of, setup_entry, state_of

STORAGE = (DEVICE_ID, "Inverter", {**DEVICE_DATA, "profile": "ingeteam.oneplay_storage"})


async def advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    # mueve el reloj (t de las muestras) y dispara los tiers vencidos
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def kwh(hass: HomeAssistant, key: str) -> float:
    return float(state_of(hass, key).state)


async def test_core_entities_and_disabled_extra(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_entry(hass, brand_entry(STORAGE))
    assert state_of(hass, "inverter_state").state == "on_grid"
    assert float(state_of(hass, "grid_power").state) == -300
    registry = er.async_get(hass)
    extra = registry.async_get(entity_id_of(hass, "dc_bus_voltage"))
    assert extra.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    energy = state_of(hass, "solar_energy")
    assert (energy.attributes["unit_of_measurement"], energy.attributes["state_class"]) == ("kWh", "total_increasing")
    assert energy.attributes["device_class"] == "energy"


async def test_energy_grows_between_reads(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    await setup_entry(hass, brand_entry(STORAGE))
    assert kwh(hass, "solar_energy") == 0
    await advance(hass, freezer, 6)
    # 3000 W durante 6 s
    assert kwh(hass, "solar_energy") == pytest.approx(0.005)
    assert kwh(hass, "grid_export_energy") == pytest.approx(300 * 6 / 3_600_000)
    assert kwh(hass, "grid_import_energy") == 0
    assert kwh(hass, "battery_discharge_energy") == pytest.approx(500 * 6 / 3_600_000)
    assert kwh(hass, "battery_charge_energy") == 0


async def test_read_failure_adds_no_energy(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    await setup_entry(hass, brand_entry(STORAGE))
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await advance(hass, freezer, 6)
    storage_unit.fail_requests(None)
    await advance(hass, freezer, 6)
    # el tramo con el fallo no se integra
    assert kwh(hass, "solar_energy") == 0
    await advance(hass, freezer, 6)
    assert kwh(hass, "solar_energy") == pytest.approx(0.005)


async def test_energy_survives_reload(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    entry = brand_entry(STORAGE)
    await setup_entry(hass, entry)
    await advance(hass, freezer, 6)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert kwh(hass, "solar_energy") == pytest.approx(0.005)
    await advance(hass, freezer, 6)
    assert kwh(hass, "solar_energy") == pytest.approx(0.01)


async def test_energy_restored_after_restart(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("sensor.inverter_solar_energy", "1.5"),
                {"native_value": 1.5, "native_unit_of_measurement": "kWh"},
            )
        ],
    )
    await setup_entry(hass, brand_entry(STORAGE))
    assert entity_id_of(hass, "solar_energy") == "sensor.inverter_solar_energy"
    assert kwh(hass, "solar_energy") == 1.5


async def test_energy_counts_with_power_sensor_disabled(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    entry = brand_entry(STORAGE)
    entry.add_to_hass(hass)
    for key in ("pv1_power", "pv2_power"):
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"{DEVICE_ID}_{key}", config_entry=entry, config_subentry_id=DEVICE_ID,
            disabled_by=er.RegistryEntryDisabler.USER,
        )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    await advance(hass, freezer, 6)
    assert kwh(hass, "solar_energy") == pytest.approx(0.005)
```

- [ ] **Step 2:** lint, commit `test(red): energy sensors`, CI → rojo (`solar_energy` sin entidad).

- [ ] **Step 3: implementación.** `entities/base.py`: `spec: EntitySpec | EnergySpec`;
  `entity_category` solo si `isinstance(spec, EntitySpec)`.

`entities/energy.py`:

```python
"""Sensor de energía calculada: integra la suma de sus fuentes de potencia."""

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from ....domain.energy import EnergyAccumulator, EnergySpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


class ModbusSolarEnergySensor(ModbusSolarEntity, RestoreSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3

    def __init__(
        self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: EnergySpec, brand_device_id: str
    ) -> None:
        super().__init__(coordinator, runtime, spec, brand_device_id)
        self._energy = spec
        # tres intervalos sin muestra = hueco que no se integra
        self._max_gap_s = 3 * runtime.intervals[coordinator.tier]
        self._accumulator = EnergyAccumulator(spec.sign, self._max_gap_s)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and isinstance(last.native_value, int | float):
            # lo que pasa con HA apagado no se integra: se sigue desde el último total
            self._accumulator = EnergyAccumulator(self._energy.sign, self._max_gap_s, float(last.native_value))
        self._sample()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sample()
        super()._handle_coordinator_update()

    def _sample(self) -> None:
        self._accumulator.add(dt_util.utcnow().timestamp(), self._source_power())

    def _source_power(self) -> float | None:
        data = self.coordinator.data
        if not self.coordinator.last_update_success or data is None:
            return None
        values = [data.values.get(key) for key in self._energy.sources]
        # una fuente sin valor (decode o lectura fallida) corta la serie
        if any(not isinstance(value, int | float) for value in values):
            return None
        return float(sum(values))

    @property
    def native_value(self) -> float:
        return self._accumulator.total_kwh
```

`entities/factory.py`:

```python
def build_sensors(runtime: DeviceRuntime, brand_device_id: str) -> list[SensorEntity]:
    sensors: list[SensorEntity] = [
        ModbusSolarSensor(runtime.coordinators[spec.poll], runtime, spec, brand_device_id)
        for spec in runtime.profile.entities
        if spec.platform is Platform.SENSOR
    ]
    by_key = {spec.key: spec for spec in runtime.profile.entities}
    for energy in runtime.profile.energies:
        # validate_profile garantiza que todas las fuentes van en el mismo tier
        coordinator = runtime.coordinators[by_key[energy.sources[0]].poll]
        sensors.append(ModbusSolarEnergySensor(coordinator, runtime, energy, brand_device_id))
    return sensors
```

- [ ] **Step 4:** lint, commit `feat: computed energy sensors with restore`, CI → verde.

---

### Tarea 7: documentación y ADR

**Files:**
- Create: `docs/decisions/0009-computed-energy.md`
- Modify: `docs/architecture/domain.md`, `docs/architecture/application.md`,
  `docs/architecture/adapters/inbound.md`, `docs/architecture/adapters/outbound.md`,
  `docs/features/monitoring.md`, `docs/features/device-setup.md`, `docs/guides/setup.md`,
  `docs/README.md`, `README.md`, front-matter de `spec.md` y `plan.md`

- [ ] **Step 1:** citas `archivo:línea` vivas para `max_gap`, `EnergySpec`,
  `EnergyAccumulator`, `always_update`, `enabled_keys` y `ModbusSolarEnergySensor`. Comprobar
  cada cita con `grep -n`.
- [ ] **Step 2:** `features/monitoring.md`: perfiles, entidades del núcleo y extra, energías,
  signos supuestos y panel de Energía. `guides/setup.md`: límites de `ABH2014IQM01` y entidad
  huérfana `total_energy`. `README.md`: equipos soportados.
- [ ] **Step 3:** ADR 0009 «Energía calculada por la integración cuando el equipo no la da».
- [ ] **Step 4:** `status: done` en spec y plan; lint; commit `docs: STORAGE profile and computed energy`;
  `bash scripts/ci-wait.sh` y `bash scripts/ci-wait.sh validate.yml`, uno detrás de otro.
