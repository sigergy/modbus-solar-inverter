---
type: feature
area: config-flow
layers: [domain, application, adapters, profiles]
status: done
date: 2026-10-05
---

# Plan de implementación — Spec 4, flujo de configuración v2

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `subagent-driven-development` (recomendada) o `executing-plans`
> para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** implementar la [spec](spec.md): alta en pasos marca → modelo → conexión → componentes → lecturas →
nombre → intervalos; un dispositivo de HA por componente con Device ID; bits del BMS como `binary_sensor`; número
de serie opcional; tier `instant` con validación de presupuesto; reconfigure en tres pasos más el renombrado.

**Arquitectura:** hexagonal, vigilada por import-linter. El dominio (`domain/`) gana los tipos y la validación;
`application/` gana la selección por componentes, el presupuesto y la sonda con serie; los adaptadores
(`adapters/inbound/`) construyen dispositivos, entidades y el config flow. `domain`, `ports`, `application` y
`profiles` no importan HA.

**Stack:** Python 3.14, Home Assistant 2026.9.4, pytest con `pytest-homeassistant-custom-component` (solo en CI),
ruff (línea de 120), import-linter, hassfest y HACS en `validate.yml`.

Rutas de código relativas a `custom_components/modbus_solar/` salvo indicación.

## Global Constraints

- Rama `feat/setup-flow-v2` con base `main`, en el worktree hijo de Orca `setup-flow-v2` (Tarea 0). Push autorizado a esa rama con
  `bash scripts/ci-wait.sh`, lanzado en segundo plano. Force push, merge, rebase y PR piden confirmación.
- Tests solo en CI: nunca `pytest` en local. El gate local es `bash scripts/lint.sh` antes de cada commit.
- Cada tarea: commit `test(red): …` con los tests que fallan (CI en rojo por esos tests y solo esos), y después
  commit `feat: …` (o `refactor: …`, `docs: …`) con CI en verde.
- Trailer obligatorio en cada commit:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01VCSruRstdih3pxjiCt94SL
  ```
- Comentarios en español; identificadores, ficheros y tests en inglés. Dentro del paquete, solo imports relativos.
- Antes de orientarse, `graft ask "<pregunta>" --source` o `graft grep "<símbolo>"`; antes de cambiar una firma,
  `graft callers <símbolo> --depth 2`. `graft/` y `.graft_*` no se commitean nunca.
- `VERSION` del flujo sigue en 2; sin `async_migrate_entry` (spec §8). `unique_id` de entry y entidades no cambia.
- No inventar: si una API (de HA o del código) no se comporta como dice el plan, parar y avisar con la salida
  real. Las citas `archivo:línea` de este plan son de `4cb3d91`; tras cada tarea pueden moverse.

## Mapa de ficheros

| Fichero | Cambio | Tarea |
|---|---|---|
| `domain/types.py` | `PollTier.INSTANT`, `Component`, `Platform.BINARY_SENSOR`, `Role.BMS_ALARM/BMS_FLAG`, `DataType.ASCII` | 1, 2, 3 |
| `domain/profile.py` | `RegisterSpec.length` y `words`, `EntitySpec.bit/component`, `ComponentSpec`, `DeviceProfile.components/serial` | 2, 3, 4 |
| `domain/energy.py`, `domain/control.py` | `component` | 4 |
| `domain/decode.py` | `reg.words`, bit → `bool`, `decode_text` | 2, 3 |
| `domain/blocks.py`, `adapters/outbound/modbus_gateway.py` | `reg.dtype.words` → `reg.words` | 2 |
| `domain/validate.py` | `reg.words`, `serial`, bits y solape, componentes | 2, 3, 4 |
| `application/selection.py` | nuevo: `Selection`, `select` | 5 |
| `application/poller.py` | `request_rate` | 1 |
| `application/probe.py` | `ProbeResult`, tier `instant`, serie | 6 |
| `profiles/ingeteam/oneplay_storage.py` | red en `instant`, `_extra` con tier, componentes, bits del BMS | 1, 7 |
| `const.py` | `DEFAULT_INTERVALS`, `CONF_COMPONENTS`, `CONF_DEVICE_ID`, `CONF_SERIAL_NUMBER` | 1, 8 |
| `adapters/inbound/entities/base.py` | `DeviceInfo` por componente con Device ID y serie | 9 |
| `adapters/inbound/entities/binary_sensor.py`, `binary_sensor.py` | nuevos: plataforma `binary_sensor` | 10 |
| `adapters/inbound/entities/factory.py` | fábrica de `binary_sensor`; selección | 10 |
| `adapters/inbound/entities/energy.py` | `max_gap_s` según el intervalo del tier | 1 |
| `adapters/inbound/runtime.py`, `__init__.py` | componentes elegidos, limpieza del registro, `PLATFORMS` | 8, 10 |
| `adapters/inbound/diagnostics.py` | redacta `serial_number` | 9 |
| `adapters/inbound/flow.py` | pasos nuevos de alta y reconfigure | 11-15 |
| `manifest.json` | `integration_type: hub` | 9 |
| `strings.json`, `translations/en.json`, `translations/es.json` | textos (spec §6) | 7, 9, 11-15 |
| `tests/fakes.py` | perfil falso con otro `device_type` | 13 |
| `tests/unit/*`, `tests/ha/*` | ver cada tarea | 1-15 |
| `docs/…`, `CHANGELOG.md`, `README.md`, wiki | sync | 16 |

---

### Tarea 0: rama

La crea el orquestador antes de ejecutar el plan, con la skill `orca-cli`: worktree hijo `setup-flow-v2`, rama
`feat/setup-flow-v2` con base `main` (que ya incluye esta spec y este plan).

- [ ] **Step 1:** dentro del worktree, comprobar la rama y la base, y publicarla:

```bash
git status -sb                      # ## feat/setup-flow-v2, árbol limpio
git merge-base --is-ancestor origin/main HEAD && echo OK
git push -u origin feat/setup-flow-v2
```

---

## Fase 1 — dominio y perfil

### Tarea 1: tier `instant` y presupuesto de peticiones

**Files:**
- Modify: `domain/types.py:27-30`, `application/poller.py:46-49`, `const.py:10`,
  `profiles/ingeteam/oneplay_storage.py:178,180,188`, `adapters/inbound/entities/energy.py:24`,
  `strings.json`, `translations/en.json`, `translations/es.json`
- Test: `tests/unit/test_poller.py`, `tests/unit/test_storage_profile.py:180-182`, `tests/ha/test_config_flow.py:77`,
  `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: `min_tier_interval(profile, tier) -> float` (`application/poller.py:46`).
- Produces: `PollTier.INSTANT = "instant"`, primero del enum;
  `request_rate(profile: DeviceProfile, intervals: Mapping[PollTier, int]) -> float`;
  `DEFAULT_INTERVALS = {"instant": 5, "fast": 10, "normal": 60, "slow": 3600}`.

- [ ] **Step 1: tests que fallan**

`tests/unit/test_poller.py`, al final:

```python
from custom_components.modbus_solar.application.poller import request_rate
from custom_components.modbus_solar.const import DEFAULT_INTERVALS
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import PROFILE as STORAGE


def defaults() -> dict[PollTier, int]:
    return {tier: DEFAULT_INTERVALS[tier.value] for tier in PollTier}


def test_request_rate_with_defaults_fits_one_per_second() -> None:
    assert request_rate(STORAGE, defaults()) <= 1


def test_request_rate_instant_one_second_exceeds_budget() -> None:
    assert request_rate(STORAGE, defaults() | {PollTier.INSTANT: 1}) > 1


def test_request_rate_ignores_tiers_without_entities() -> None:
    # solo cuentan los tiers del mapa; un tier ausente no suma
    assert request_rate(STORAGE, {PollTier.SLOW: 3600}) == pytest.approx(3 / 3600)
```

Antes de escribirlo, comprobar con `grep -n "^from\|^import\|PROFILE" tests/unit/test_poller.py
profiles/ingeteam/oneplay_storage.py` el nombre real de la constante del perfil y los imports que ya existen; no
duplicarlos. El valor de `slow` es 3 bloques tras la Tarea 7; en esta tarea todavía son 6: el tercer test
usa `min_tier_interval(STORAGE, PollTier.SLOW) / 3600` en lugar del literal.

`tests/unit/test_storage_profile.py:180-182`: añadir `assert min_tier_interval(PROFILE, PollTier.INSTANT) == 1.0`.

`tests/ha/test_config_flow.py:77`: el diccionario esperado de intervalos gana `"instant": 5` y `"fast": 10`.

`tests/unit/test_translations.py`: cada paso con intervalos (`connection`/`reconfigure` hoy; `intervals` y
`reconfigure_intervals` en la Tarea 14) tiene la sección `instant` en `strings.json` y en `es.json`. Buscar el
test actual que recorre `PollTier` y comprobar que ya falla por la clave nueva; si no hay, añadir:

```python
def test_interval_sections_cover_every_tier() -> None:
    step = STRINGS["config"]["step"]["reconfigure"]
    for tier in PollTier:
        assert tier.value in step["sections"], tier
```

Ajustar `STRINGS` y la ruta de la sección al nombre real del fichero (`grep -n "sections\|PollTier"
tests/unit/test_translations.py`).

- [ ] **Step 2:** `bash scripts/lint.sh`; commit `test(red): instant tier and request budget`; push y
  `bash scripts/ci-wait.sh` → rojo en estos tests.

- [ ] **Step 3: implementación**

`domain/types.py`:

```python
class PollTier(StrEnum):
    INSTANT = "instant"  # primero: el formulario de intervalos recorre el enum en orden
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"
```

`application/poller.py`, tras `min_tier_interval`:

```python
def request_rate(profile: DeviceProfile, intervals: Mapping[PollTier, int]) -> float:
    """Peticiones por segundo que piden los tiers con estos intervalos. El equipo admite 1."""
    return sum(min_tier_interval(profile, tier) / interval for tier, interval in intervals.items())
```

(`from collections.abc import Collection, Mapping`.)

`const.py:10`: `DEFAULT_INTERVALS = {"instant": 5, "fast": 10, "normal": 60, "slow": 3600}`.

`profiles/ingeteam/oneplay_storage.py:178,180,188`: `grid_voltage`, `grid_frequency` y `grid_power` pasan a
`poll=PollTier.INSTANT`.

`adapters/inbound/entities/energy.py:24`: el `max_gap_s` deja de ser fijo y vale 3 × el intervalo del tier de la
energía. Leer la línea y cómo llega el intervalo al constructor antes de tocar; si el intervalo no llega, pasarlo
desde la fábrica (`adapters/inbound/entities/factory.py`) con el valor de `intervals[tier]`.

Traducciones: sección `instant` en cada paso que hoy tiene `fast`, con etiqueta «Instantánea» / «Instant».
`translations/en.json` es copia literal de `strings.json`.

- [ ] **Step 4:** lint; commit `feat: instant poll tier and request budget`; push y ci-wait → verde.

### Tarea 2: tipo ASCII y `RegisterSpec.words`

**Files:**
- Modify: `domain/types.py:6-19`, `domain/profile.py:11-18`, `domain/decode.py`, `domain/blocks.py:20,30`,
  `adapters/outbound/modbus_gateway.py:54`, `domain/validate.py:14,94`
- Test: `tests/unit/test_types.py`, `tests/unit/test_decode.py`, `tests/unit/test_validate.py`

**Interfaces:**
- Produces: `DataType.ASCII = "ascii"`; `RegisterSpec.length: int = 0`; propiedad `RegisterSpec.words -> int`;
  `DataType.words` lanza `ValueError` con `ASCII`; `decode_text(register: RegisterSpec, words: Sequence[int]) -> str`;
  `DeviceProfile.serial: RegisterSpec | None = None`.

- [ ] **Step 1: tests que fallan**

`tests/unit/test_types.py`:

```python
def test_ascii_words_come_from_register_length() -> None:
    with pytest.raises(ValueError):
        DataType.ASCII.words
    assert RegisterSpec(address=0, dtype=DataType.ASCII, length=5).words == 5
    assert RegisterSpec(address=0, dtype=DataType.U32).words == 2
```

`tests/unit/test_decode.py`:

```python
def test_text_strips_nulls_and_trailing_spaces() -> None:
    reg = RegisterSpec(address=0, dtype=DataType.ASCII, length=3)
    assert decode_text(reg, (0x4142, 0x3120, 0x0000)) == "AB1"


def test_text_wrong_word_count_raises() -> None:
    reg = RegisterSpec(address=0, dtype=DataType.ASCII, length=3)
    with pytest.raises(DecodeError, match="expected 3 words"):
        decode_text(reg, (0x4142,))
```

`tests/unit/test_validate.py`:

```python
def test_serial_must_be_ascii_with_length() -> None:
    good = RegisterSpec(address=100, dtype=DataType.ASCII, length=8)
    assert validate_profile(replace(profile(ent("a", 0)), serial=good)) == []
    bad_type = RegisterSpec(address=100, dtype=DataType.U16)
    assert validate_profile(replace(profile(ent("a", 0)), serial=bad_type)) == ["serial: dtype must be ascii"]
    no_length = RegisterSpec(address=100, dtype=DataType.ASCII)
    assert validate_profile(replace(profile(ent("a", 0)), serial=no_length)) == ["serial: length must be >= 1"]


def test_entity_cannot_be_ascii() -> None:
    reg = RegisterSpec(address=0, dtype=DataType.ASCII, length=2)
    problems = validate_profile(profile(replace(ent("a", 0), register=reg)))
    assert problems == ["a: ascii only for serial"]
```

- [ ] **Step 2:** lint; commit `test(red): ascii register type`; push y ci-wait → rojo.

- [ ] **Step 3: implementación**

`domain/types.py`:

```python
class DataType(StrEnum):
    U16 = "u16"
    S16 = "s16"
    U32 = "u32"
    S32 = "s32"
    ASCII = "ascii"  # texto de N registros; N en RegisterSpec.length

    @property
    def words(self) -> int:
        """Número de registros de 16 bits que ocupa. ASCII depende del registro: usar RegisterSpec.words."""
        if self is DataType.ASCII:
            raise ValueError("ascii length is per register")
        return 1 if self in (DataType.U16, DataType.S16) else 2
```

`domain/profile.py`, en `RegisterSpec`:

```python
    length: int = 0  # registros del texto; solo para DataType.ASCII

    @property
    def words(self) -> int:
        return self.length if self.dtype is DataType.ASCII else self.dtype.words
```

y en `DeviceProfile`: `serial: RegisterSpec | None = None  # número de serie por Modbus, opcional`.

Sustituir `reg.dtype.words` por `reg.words` en `domain/blocks.py:20,30`, `adapters/outbound/modbus_gateway.py:54`,
`domain/decode.py:12` y `domain/validate.py:14,94` (confirmar con `grep -rn "dtype.words" custom_components`).

`domain/decode.py`:

```python
def decode_text(register: RegisterSpec, words: Sequence[int]) -> str:
    """Texto ASCII, dos caracteres por palabra con el alto primero; sin nulos ni espacios al final."""
    if len(words) != register.words:
        raise DecodeError(f"text: expected {register.words} words, got {len(words)}")
    data = b"".join(word.to_bytes(2, "big") for word in words)
    return data.decode("ascii", errors="replace").rstrip("\x00 ")
```

`domain/validate.py`: un problema `"<key>: ascii only for serial"` por entidad ASCII; y si `profile.serial`:
`"serial: dtype must be ascii"` o `"serial: length must be >= 1"`.

- [ ] **Step 4:** lint; commit `feat: ascii register type for serial number`; push y ci-wait → verde.

### Tarea 3: bits como `binary_sensor` en el dominio

**Files:**
- Modify: `domain/types.py`, `domain/profile.py:21-33`, `domain/decode.py`, `domain/validate.py:81-82`
- Test: `tests/unit/test_decode.py`, `tests/unit/test_validate.py`

**Interfaces:**
- Produces: `Platform.BINARY_SENSOR = "binary_sensor"`; `Role.BMS_ALARM = "bms_alarm"`, `Role.BMS_FLAG = "bms_flag"`;
  `EntitySpec.bit: int | None = None`; `decode(...) -> int | float | str | bool`.

- [ ] **Step 1: tests que fallan**

`tests/unit/test_decode.py`:

```python
def test_bit_decodes_to_bool() -> None:
    spec = replace(entity(DataType.U16), platform=Platform.BINARY_SENSOR, bit=3)
    assert decode(spec, (0b1000,)) is True
    assert decode(spec, (0b0111,)) is False
```

`tests/unit/test_validate.py` (helper nuevo `flag`):

```python
def flag(key: str, address: int, bit: int, dtype: DataType = DataType.U16) -> EntitySpec:
    return replace(ent(key, address, dtype), platform=Platform.BINARY_SENSOR, bit=bit)


def test_bits_may_share_a_register() -> None:
    assert validate_profile(profile(ent("a", 0), flag("b0", 5, 0), flag("b1", 5, 1))) == []


def test_bit_and_plain_entity_still_overlap() -> None:
    assert validate_profile(profile(ent("a", 5), flag("b0", 5, 0))) == ["b0: overlaps a"]


def test_bit_rules() -> None:
    assert validate_profile(profile(ent("a", 0), flag("b", 5, 16))) == ["b: bit out of range"]
    assert validate_profile(profile(ent("a", 0), flag("b", 5, 0, DataType.U32))) == ["b: bit requires u16"]
    no_bit = replace(ent("b", 5), platform=Platform.BINARY_SENSOR)
    assert validate_profile(profile(ent("a", 0), no_bit)) == ["b: binary_sensor requires bit"]
    sensor_bit = replace(ent("b", 5), bit=0)
    assert validate_profile(profile(ent("a", 0), sensor_bit)) == ["b: bit requires binary_sensor"]
```

El texto del solape (`"b0: overlaps a"`) se copia del mensaje real de `domain/validate.py:81-82`; si es otro, se
usa el real.

- [ ] **Step 2:** lint; commit `test(red): bit entities`; push y ci-wait → rojo.

- [ ] **Step 3: implementación**

- `Platform.BINARY_SENSOR = "binary_sensor"`; `Role.BMS_ALARM`, `Role.BMS_FLAG` junto a `DIAGNOSTIC`.
- `EntitySpec`: `bit: int | None = None  # bit de un U16; exige platform binary_sensor`.
- `decode`, tras calcular `raw` y antes del enum: `if entity.bit is not None: return bool(raw >> entity.bit & 1)`.
- `validate.py`: las cuatro reglas del test, con esos textos; el control de solape ignora el par si las dos
  entidades llevan `bit`.

- [ ] **Step 4:** lint; commit `feat: bit entities decode to bool`; push y ci-wait → verde.

### Tarea 4: componentes en el dominio

**Files:**
- Modify: `domain/types.py`, `domain/profile.py`, `domain/energy.py`, `domain/control.py`, `domain/validate.py`
- Test: `tests/unit/test_validate.py`

**Interfaces:**
- Produces: `Component(StrEnum)`: `MAIN="main"`, `PV="pv"`, `BATTERY="battery"`, `GRID="grid"`,
  `INTERNAL_METER="internal_meter"`, `CRITICAL_LOADS="critical_loads"`, `LOAD="load"`, `EV_CHARGER="ev_charger"`;
  `ComponentSpec(component: Component, default: bool = True)` en `domain/profile.py`;
  `component: Component = Component.MAIN` en `EntitySpec`, `EnergySpec`, `GatedLimitSpec`;
  `DeviceProfile.components: tuple[ComponentSpec, ...] = ()`.

- [ ] **Step 1: tests que fallan**

```python
def with_components(*entities: EntitySpec, components: tuple[ComponentSpec, ...]) -> DeviceProfile:
    return replace(profile(*entities), components=components)


def test_components_valid() -> None:
    entities = (ent("a", 0), replace(ent("b", 1), component=Component.BATTERY))
    assert validate_profile(with_components(*entities, components=(ComponentSpec(Component.BATTERY),))) == []


def test_component_not_declared() -> None:
    entities = (ent("a", 0), replace(ent("b", 1), component=Component.BATTERY))
    assert validate_profile(with_components(*entities, components=())) == ["b: component battery not declared"]


def test_components_no_main_no_repeats_no_empty() -> None:
    battery = ComponentSpec(Component.BATTERY)
    entities = (ent("a", 0), replace(ent("b", 1), component=Component.BATTERY))
    assert validate_profile(with_components(*entities, components=(battery, battery))) == [
        "components: battery repeated"
    ]
    assert validate_profile(with_components(*entities, components=(ComponentSpec(Component.MAIN), battery))) == [
        "components: main is implicit"
    ]
    assert validate_profile(with_components(ent("a", 0), components=(battery,))) == ["components: battery is empty"]


def test_energy_in_component_of_its_sources() -> None:
    entities = (power("a", 0), replace(power("b", 1), component=Component.PV))
    bad = replace(with_energies(energy("e", "b"), entities=entities), components=(ComponentSpec(Component.PV),))
    assert validate_profile(bad) == ["e: component differs from sources"]
```

- [ ] **Step 2:** lint; commit `test(red): profile components`; push y ci-wait → rojo.

- [ ] **Step 3: implementación**

`Component` en `domain/types.py`; `ComponentSpec` frozen y `kw_only=False` (se construye posicional en los
tests) en `domain/profile.py`; los campos `component` y `components`; las cuatro reglas en `validate.py` con
esos textos. Las energías y los controles cuentan para «componente no vacío».

- [ ] **Step 4:** lint; commit `feat: profile components`; push y ci-wait → verde.

### Tarea 5: selección por componentes

**Files:**
- Create: `application/selection.py`
- Test: `tests/unit/test_selection.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True)
  class Selection:
      entities: tuple[EntitySpec, ...]
      energies: tuple[EnergySpec, ...]
      controls: tuple[GatedLimitSpec, ...]

  def select(profile: DeviceProfile, components: Collection[Component] | None) -> Selection
  ```
  `None` = todos los opcionales del perfil (entries anteriores, spec §8). `MAIN` va siempre.

- [ ] **Step 1: tests que fallan** (`tests/unit/test_selection.py`)

```python
"""Selección de entidades, energías y controles por componentes elegidos."""

from dataclasses import replace

from custom_components.modbus_solar.application.selection import select
from custom_components.modbus_solar.domain.profile import ComponentSpec
from custom_components.modbus_solar.domain.types import Component
from tests.unit.test_validate import ent, profile


def two_components():
    entities = (ent("a", 0), replace(ent("b", 1), component=Component.BATTERY), replace(ent("c", 2), component=Component.PV))
    return replace(profile(*entities), components=(ComponentSpec(Component.PV), ComponentSpec(Component.BATTERY)))


def test_main_always_selected() -> None:
    assert [e.key for e in select(two_components(), []).entities] == ["a"]


def test_selected_components_in_profile_order() -> None:
    assert [e.key for e in select(two_components(), [Component.BATTERY]).entities] == ["a", "b"]


def test_none_means_all_optional() -> None:
    assert [e.key for e in select(two_components(), None).entities] == ["a", "b", "c"]
```

Si importar helpers de otro test no es la costumbre del repo (`grep -rn "from tests" tests/`), copiar `ent` y
`profile` a `tests/fakes.py` y usarlos desde allí.

- [ ] **Step 2:** lint; commit `test(red): component selection`; push y ci-wait → rojo.

- [ ] **Step 3: implementación** (`application/selection.py`)

```python
"""Entidades, energías y controles de los componentes elegidos. La usan runtime, flujo y diagnóstico."""

from collections.abc import Collection
from dataclasses import dataclass

from ..domain.control import GatedLimitSpec
from ..domain.energy import EnergySpec
from ..domain.profile import DeviceProfile, EntitySpec
from ..domain.types import Component


@dataclass(frozen=True)
class Selection:
    entities: tuple[EntitySpec, ...]
    energies: tuple[EnergySpec, ...]
    controls: tuple[GatedLimitSpec, ...]


def select(profile: DeviceProfile, components: Collection[Component] | None) -> Selection:
    # None = entry anterior a v2: todos los opcionales
    chosen = {c.component for c in profile.components} if components is None else set(components)
    chosen.add(Component.MAIN)
    return Selection(
        entities=tuple(e for e in profile.entities if e.component in chosen),
        energies=tuple(e for e in profile.energies if e.component in chosen),
        controls=tuple(c for c in profile.controls if c.component in chosen),
    )
```

- [ ] **Step 4:** lint; commit `feat: component selection`; push y ci-wait → verde.

### Tarea 6: sonda con `instant` y número de serie

**Files:**
- Modify: `application/probe.py`
- Test: `tests/unit/test_probe.py`

**Interfaces:**
- Consumes: `read_tier`, `TierResult` (`application/poller.py`), `decode_text` (Tarea 2).
- Produces: `ProbeResult(readings: TierResult, serial: str | None)`;
  `probe_device(gateway, profile) -> ProbeResult`. `readings` = valores de `fast` + `instant`. Un fallo al leer o
  decodificar el serie da `serial=None` sin fallar la sonda.

- [ ] **Step 1: tests que fallan** (`tests/unit/test_probe.py`, con el gateway falso que ya usa el fichero)

```python
async def test_probe_reads_fast_and_instant() -> None:
    result = await probe_device(gateway_with(STORAGE_WORDS), STORAGE)
    assert {"active_power", "grid_power"} <= result.readings.values.keys()


async def test_probe_serial_none_when_profile_has_no_register() -> None:
    assert (await probe_device(gateway_with(STORAGE_WORDS), STORAGE)).serial is None


async def test_probe_reads_serial() -> None:
    reg = RegisterSpec(address=900, dtype=DataType.ASCII, length=2)
    words = STORAGE_WORDS | {reg: (0x4142, 0x3100)}
    assert (await probe_device(gateway_with(words), replace(STORAGE, serial=reg))).serial == "AB1"


async def test_probe_serial_failure_does_not_fail_probe() -> None:
    reg = RegisterSpec(address=900, dtype=DataType.ASCII, length=2)
    result = await probe_device(failing_on(reg, gateway_with(STORAGE_WORDS)), replace(STORAGE, serial=reg))
    assert result.serial is None
    assert result.readings.values
```

`gateway_with`, `failing_on` y `STORAGE_WORDS`: usar los helpers reales de `tests/fakes.py`
(`grep -n "def \|class " tests/fakes.py`); si falta uno que falle en un registro concreto, añadirlo allí.
Actualizar los tests existentes de `test_probe.py` y los llamadores (`graft callers probe_device`) a
`.readings`.

- [ ] **Step 2:** lint; commit `test(red): probe reads instant tier and serial`; push y ci-wait → rojo.

- [ ] **Step 3: implementación**

```python
@dataclass(frozen=True)
class ProbeResult:
    readings: TierResult  # fast + instant: lo que coteja el paso de lecturas
    serial: str | None


async def probe_device(gateway: DeviceGateway, profile: DeviceProfile) -> ProbeResult:
    spec = next(e for e in profile.entities if e.key == profile.probe_key)
    words = await gateway.read([spec.register])
    # DecodeError si el valor no es válido (por ejemplo, fuera del enum)
    decode(spec, words[spec.register])
    keys = {e.key for e in profile.entities if e.enabled_default}
    fast = await read_tier(PollTier.FAST, gateway, profile, keys)
    instant = await read_tier(PollTier.INSTANT, gateway, profile, keys)
    readings = TierResult(
        values=fast.values | instant.values,
        raw=fast.raw | instant.raw,
        decode_errors=fast.decode_errors | instant.decode_errors,
    )
    return ProbeResult(readings=readings, serial=await _read_serial(gateway, profile))


async def _read_serial(gateway: DeviceGateway, profile: DeviceProfile) -> str | None:
    if profile.serial is None:
        return None
    try:
        words = await gateway.read([profile.serial])
        return decode_text(profile.serial, words[profile.serial]) or None
    except (DecodeError, DeviceUnavailable, DeviceProtocolError):
        # el número de serie es opcional: su fallo no invalida la sonda
        return None
```

Las excepciones del gateway salen de `domain/errors.py` (las que importa hoy `adapters/inbound/flow.py:33`).
Ajustar los llamadores del flujo a `result.readings` sin cambiar comportamiento.

- [ ] **Step 4:** lint; commit `feat: probe reads instant tier and optional serial`; push y ci-wait → verde.

### Tarea 7: perfil STORAGE — componentes, extras y bits del BMS

**Files:**
- Modify: `profiles/ingeteam/oneplay_storage.py` (`_extra` en `:74-94`), `strings.json`, `translations/en.json`,
  `translations/es.json`
- Test: `tests/unit/test_storage_profile.py`, `tests/unit/test_profiles.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: `Component`, `ComponentSpec`, `bit`, `Platform.BINARY_SENSOR`, `Role.BMS_*`.
- Produces: reparto de la spec §5.1; `components=(pv, battery, grid, internal_meter[default=False],
  critical_loads, load, ev_charger[default=False])` en ese orden; 14 bits de §5.3; tiers de §5.7.

- [ ] **Step 1: tests que fallan** (`tests/unit/test_storage_profile.py`)

```python
def test_tier_minimums() -> None:
    assert min_tier_interval(PROFILE, PollTier.INSTANT) == 1.0
    assert min_tier_interval(PROFILE, PollTier.FAST) == 6.0
    assert min_tier_interval(PROFILE, PollTier.NORMAL) == 5.0
    assert min_tier_interval(PROFILE, PollTier.SLOW) == 3.0


def test_entities_per_component() -> None:
    counts = Counter(e.component for e in PROFILE.entities)
    counts.update(e.component for e in PROFILE.energies)
    counts.update(c.component for c in PROFILE.controls)  # cada control da número y switch: cuenta 2
    counts.update(c.component for c in PROFILE.controls)
    assert counts == {
        Component.MAIN: 13, Component.PV: 8, Component.BATTERY: 25, Component.GRID: 5,
        Component.INTERNAL_METER: 4, Component.CRITICAL_LOADS: 4, Component.LOAD: 1, Component.EV_CHARGER: 1,
    }


def test_optional_components_and_defaults() -> None:
    assert [(c.component, c.default) for c in PROFILE.components] == [
        (Component.PV, True), (Component.BATTERY, True), (Component.GRID, True),
        (Component.INTERNAL_METER, False), (Component.CRITICAL_LOADS, True), (Component.LOAD, True),
        (Component.EV_CHARGER, False),
    ]


BMS_BITS = {
    "bms_alarm_high_charge_current": (28, 0), "bms_alarm_high_voltage": (28, 1), "bms_alarm_low_voltage": (28, 2),
    "bms_alarm_high_temperature": (28, 3), "bms_alarm_low_temperature": (28, 4), "bms_alarm_internal": (28, 5),
    "bms_alarm_cell_imbalance": (28, 6), "bms_alarm_high_discharge_current": (28, 7),
    "bms_alarm_system_error": (28, 8), "bms_stop_charge": (68, 0), "bms_stop_discharge": (68, 1),
    "bms_forced_charge": (68, 2), "bms_calibration": (68, 3), "bms_forced_charge_soc": (68, 4),
}


def test_bms_bits() -> None:
    bits = {e.key: e for e in PROFILE.entities if e.bit is not None}
    assert {k: (e.register.address, e.bit) for k, e in bits.items()} == BMS_BITS
    for e in bits.values():
        assert (e.component, e.poll, e.enabled_default, e.entity_category) == (
            Component.BATTERY, PollTier.FAST, True, "diagnostic",
        )
        assert e.role is (Role.BMS_ALARM if e.key.startswith("bms_alarm_") else Role.BMS_FLAG)
        assert e.device_class == ("problem" if e.role is Role.BMS_ALARM else None)


EXTRA_TIERS = {
    "operation_time": (PollTier.SLOW, False), "reactive_power": (PollTier.FAST, False),
    "power_factor": (PollTier.FAST, False), "power_reduction_ratio": (PollTier.NORMAL, False),
    "power_reduction_reason": (PollTier.NORMAL, False), "dc_bus_voltage": (PollTier.FAST, False),
    "inverter_temperature": (PollTier.NORMAL, False), "isolation_positive": (PollTier.SLOW, False),
    "isolation_negative": (PollTier.SLOW, False), "external_pv_power": (PollTier.FAST, False),
    "battery_charge_limit_reason": (PollTier.NORMAL, False),
    "battery_discharge_limit_reason": (PollTier.NORMAL, False),
}


def test_extra_tiers_and_enabled() -> None:
    by_key = {e.key: e for e in PROFILE.entities}
    for key, (tier, enabled) in EXTRA_TIERS.items():
        assert (by_key[key].poll, by_key[key].enabled_default, by_key[key].entity_category) == (
            tier, enabled, "diagnostic",
        ), key
    for prefix in ("internal_meter_", "critical_load_", "ev_charger_"):
        for e in (e for e in PROFILE.entities if e.key.startswith(prefix)):
            assert (e.poll, e.enabled_default, e.entity_category) == (PollTier.FAST, True, None), e.key
```

Direcciones = registro − 30001 (30029 → 28, 30069 → 68). Antes de fijar las claves de `EXTRA_TIERS` y los
recuentos, cotejarlos con `profiles/ingeteam/oneplay_storage.py` y con la tabla de §5.1: si una clave real
difiere, se usa la real y se avisa.

`tests/unit/test_profiles.py`: el `brand` de cada perfil coincide con su carpeta en `profiles/` (spec §3.1).

`tests/unit/test_translations.py`: el nombre de cada entidad se busca en la sección de su plataforma
(`entity.<platform>`), no solo en `entity.sensor` (`:37`).

Sustituir los recuentos de bloques viejos de `:180-182` por `test_tier_minimums`.

- [ ] **Step 2:** lint; commit `test(red): storage components, extras tiers and bms bits`; push y ci-wait → rojo.

- [ ] **Step 3: implementación**

`_extra` gana parámetros con los valores de hoy por defecto:

```python
def _extra(
    key: str,
    address: int,
    dtype: DataType,
    *,
    poll: PollTier = PollTier.SLOW,
    enabled_default: bool = False,
    entity_category: str | None = "diagnostic",
    component: Component = Component.MAIN,
    **kwargs: Any,
) -> EntitySpec:
```

(adaptar a la firma real de `:74-94`; los argumentos que ya tiene se conservan). Bits con un helper:

```python
def _bms_bit(key: str, address: int, bit: int, role: Role) -> EntitySpec:
    return EntitySpec(
        key=key,
        role=role,
        platform=Platform.BINARY_SENSOR,
        register=RegisterSpec(address=address, kind=RegisterKind.INPUT, dtype=DataType.U16),
        poll=PollTier.FAST,
        bit=bit,
        component=Component.BATTERY,
        device_class="problem" if role is Role.BMS_ALARM else None,
        entity_category="diagnostic",
    )
```

`kind` igual que el resto de registros 3xxxx del perfil (comprobar). `component=` en cada entidad, energía y
control según la tabla §5.1. Textos: `entity.binary_sensor.<clave>.name` con los 14 nombres es/en de §5.3, y los
nombres cortos de §5.4 (30 filas) en `entity.sensor`.

- [ ] **Step 4:** lint; commit `feat: storage components, extras tiers and bms bits`; push y ci-wait → verde.

---

## Fase 2 — dispositivos, nombres y Device ID

### Tarea 8: runtime con componentes elegidos y limpieza del registro

**Files:**
- Modify: `const.py`, `__init__.py:24-40`, `adapters/inbound/runtime.py`
- Test: `tests/ha/test_init.py`

**Interfaces:**
- Consumes: `select` (Tarea 5).
- Produces: `CONF_COMPONENTS = "components"`, `CONF_DEVICE_ID = "device_id"`, `CONF_SERIAL_NUMBER = "serial_number"`.
  `build_runtime` y `enabled_keys` reciben las claves de `select(profile, components)`.

- [ ] **Step 1: tests que fallan** (`tests/ha/test_init.py`)

```python
async def test_unselected_component_has_no_entities(hass) -> None:
    entry = await setup_storage_entry(hass, components=["pv", "grid"])
    states = hass.states.async_entity_ids("sensor")
    assert not any("battery" in s for s in states)


async def test_entry_without_components_loads_all_optional(hass) -> None:
    entry = await setup_storage_entry(hass, components=None)
    assert len(er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)) == 47 + 14


async def test_deselecting_removes_entities_and_device(hass) -> None:
    entry = await setup_storage_entry(hass, components=["battery"])
    hass.config_entries.async_update_entry(entry, data=entry.data | {"components": []})
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    assert all(not e.unique_id.endswith("_battery_soc") for e in er.async_entries_for_config_entry(registry, entry.entry_id))
    assert dr.async_get(hass).async_get_device({(DOMAIN, f"{entry.entry_id}_battery")}) is None
```

`setup_storage_entry`: helper en `tests/ha/common.py` sobre el que ya existe para montar una entry
(`grep -n "def " tests/ha/common.py tests/ha/conftest.py`), con `components` opcional en `data`.
El recuento 47 + 14 incluye las desactivadas, que están en el registro; si el helper real no las registra, se
ajusta y se avisa.

- [ ] **Step 2:** lint; commit `test(red): runtime honours selected components`; push y ci-wait → rojo.

- [ ] **Step 3: implementación**

- `const.py`: las tres constantes.
- `async_setup_entry`: `components = entry.data.get(CONF_COMPONENTS)` (None si falta); `selection = select(profile,
  None if components is None else [Component(c) for c in components])`; antes de
  `async_forward_entry_setups`, borrar del registro de entidades las de la entry cuya clave (sufijo del
  `unique_id`, `adapters/inbound/runtime.py:33-35`) no está en la selección, y del registro de dispositivos los
  `{(DOMAIN, f"{entry_id}_{component}")}` de componentes no elegidos.
- `runtime.py`: `enabled_keys` y `build_runtime` trabajan sobre `selection` y no sobre `profile.entities`.
  `intervals = DEFAULT_INTERVALS | entry.data[CONF_INTERVALS]` (`:68`) para completar `instant`.

- [ ] **Step 4:** lint; commit `feat: runtime loads selected components only`; push y ci-wait → verde.

### Tarea 9: dispositivo por componente, Device ID y número de serie

**Files:**
- Modify: `adapters/inbound/entities/base.py:36-41`, `adapters/inbound/diagnostics.py:11`, `manifest.json:8`,
  `strings.json`, `translations/*.json`
- Test: `tests/ha/test_sensor.py`, `tests/ha/test_diagnostics.py`, `tests/unit/test_translations.py`,
  `tests/unit/test_packaging.py`, `tests/ha/test_energy.py:91,97`, `tests/ha/test_control.py:25-26`

**Interfaces:**
- Consumes: `CONF_DEVICE_ID`, `CONF_SERIAL_NUMBER`, `EntitySpec.component`.
- Produces: `device_info(entry_id, profile, component, device_id, serial) -> DeviceInfo` en `base.py`.

- [ ] **Step 1: tests que fallan**

`tests/ha/test_sensor.py`:

```python
async def test_component_device_with_device_id(hass) -> None:
    entry = await setup_storage_entry(hass, components=["battery"], device_id=0)
    device = dr.async_get(hass).async_get_device({(DOMAIN, f"{entry.entry_id}_battery")})
    main = dr.async_get(hass).async_get_device({(DOMAIN, entry.entry_id)})
    assert device.name == "Battery 0"
    assert device.via_device_id == main.id
    assert hass.states.get("sensor.battery_0_voltage") is not None


async def test_device_without_device_id(hass) -> None:
    entry = await setup_storage_entry(hass, components=["battery"], device_id=None)
    device = dr.async_get(hass).async_get_device({(DOMAIN, f"{entry.entry_id}_battery")})
    assert device.name == "Battery"


async def test_two_entries_no_suffix(hass) -> None:
    await setup_storage_entry(hass, components=["battery"], device_id=0, host="10.0.0.1")
    await setup_storage_entry(hass, components=["battery"], device_id=1, host="10.0.0.2")
    assert hass.states.get("sensor.battery_0_voltage") and hass.states.get("sensor.battery_1_voltage")
    assert not any(s.endswith("_2") for s in hass.states.async_entity_ids("sensor"))


async def test_serial_on_main_device_only(hass) -> None:
    entry = await setup_storage_entry(hass, components=["battery"], serial_number="AB1")
    registry = dr.async_get(hass)
    assert registry.async_get_device({(DOMAIN, entry.entry_id)}).serial_number == "AB1"
    assert registry.async_get_device({(DOMAIN, f"{entry.entry_id}_battery")}).serial_number is None
```

HA en los tests usa inglés: «Battery 0», `sensor.battery_0_voltage`. `tests/ha/test_energy.py:91,97` y
`tests/ha/test_control.py:25-26` esperan `sensor.inverter_solar_energy`, `number.inverter_grid_export_limit` y
`switch.inverter_grid_export`. Con el principal llamado «Inverter» siguen valiendo los de control; `solar_energy`
pasa a `pv` → `sensor.solar_array_pv_energy`. El test de restauración de energía crea antes la entidad en el
registro con `suggested_object_id="inverter_solar_energy"` para no depender del nombre.

`tests/ha/test_diagnostics.py`: `serial_number` sale redactado.
`tests/unit/test_packaging.py`: `integration_type == "hub"`.
`tests/unit/test_translations.py`: cada `device.<clave>` tiene su `<clave>_numbered` con `{device_id}`, en `es` y
`en`; claves: los `device_type` de los perfiles y los valores de `Component` salvo `main`.

- [ ] **Step 2:** lint; commit `test(red): device per component with device id`; push y ci-wait → rojo.

- [ ] **Step 3: implementación** (`base.py`)

```python
def device_info(
    entry_id: str, profile: DeviceProfile, component: Component, device_id: int | None, serial: str | None
) -> DeviceInfo:
    main = component is Component.MAIN
    key = profile.device_type if main else component.value
    info = DeviceInfo(
        identifiers={(DOMAIN, entry_id if main else f"{entry_id}_{component}")},
        translation_key=key if device_id is None else f"{key}_numbered",
        translation_placeholders=None if device_id is None else {"device_id": str(device_id)},
        manufacturer=BRAND_TITLES[profile.brand],
        model=profile.models[0],
    )
    if main:
        if serial:
            info["serial_number"] = serial
    else:
        info["via_device"] = (DOMAIN, entry_id)
    return info
```

`manufacturer` y `model`: copiar lo que hace hoy `base.py:36-41`. Se quita `name=runtime.title`.
`TO_REDACT` gana `CONF_SERIAL_NUMBER`. `manifest.json:8` → `"integration_type": "hub"`. Traducciones `device.*`
de §5.2 (es: Inversor, Campo solar, Batería, Red, Vatímetro interno, Cargas críticas, Consumo, Cargador VE; en:
Inverter, Solar array, Battery, Grid, Internal meter, Critical loads, Load, EV charger), cada una con
`_numbered` = «<nombre> {device_id}».

- [ ] **Step 4:** lint; commit `feat: one device per component with device id`; push y ci-wait → verde.

### Tarea 10: plataforma `binary_sensor`

**Files:**
- Create: `binary_sensor.py`, `adapters/inbound/entities/binary_sensor.py`
- Modify: `__init__.py:21`, `adapters/inbound/entities/factory.py`
- Test: `tests/ha/test_binary_sensor.py`

**Interfaces:**
- Consumes: `EntitySpec.bit`, `device_info` (Tarea 9).
- Produces: `ModbusSolarBinarySensor(ModbusSolarEntity, BinarySensorEntity)`; `is_on` = valor del coordinator.

- [ ] **Step 1: tests que fallan** (`tests/ha/test_binary_sensor.py`)

```python
async def test_bms_bits_are_binary_sensors(hass) -> None:
    await setup_storage_entry(hass, components=["battery"], words={28: (0b10,), 68: (0b1,)})
    assert hass.states.get("binary_sensor.battery_alarm_high_voltage").state == "on"
    assert hass.states.get("binary_sensor.battery_alarm_high_charge_current").state == "off"
    assert hass.states.get("binary_sensor.battery_charge_blocked").state == "on"
    assert len(hass.states.async_entity_ids("binary_sensor")) == 14
```

`words`: el mecanismo real del gateway falso de `tests/fakes.py` para fijar registros.

- [ ] **Step 2:** lint; commit `test(red): bms binary sensors`; push y ci-wait → rojo.

- [ ] **Step 3: implementación**

Copiar el patrón de `sensor.py` y de la entidad sensor de `adapters/inbound/entities/` (leerlos antes): la
plataforma filtra `spec.platform is Platform.BINARY_SENSOR`; `device_class` de HA desde la cadena;
`PLATFORMS` gana `HaPlatform.BINARY_SENSOR`.

- [ ] **Step 4:** lint; commit `feat: binary sensor platform for bms bits`; push y ci-wait → verde.

---

## Fase 3 — config flow y textos

Todas las tareas de esta fase tocan `adapters/inbound/flow.py` (205 líneas en `4cb3d91`) y
`tests/ha/test_config_flow.py`. Leer el fichero entero antes de cada una.

### Tarea 11: pasos `user` (marca) y `model`

**Files:** `adapters/inbound/flow.py:88-95`, textos, `tests/ha/test_config_flow.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Produces: `profile_option(profile_id: str) -> str` = `profile_id.replace(".", "_")`, clave y `value` del
  selector; el flujo la deshace buscando en `catalog.for_brand(brand)`.

- [ ] **Step 1: tests que fallan**

```python
async def test_brand_then_model(hass) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"brand": "ingeteam"})
    assert result["step_id"] == "model"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"profile": "ingeteam_oneplay_storage"})
    assert result["step_id"] == "connection"
```

`test_translations.py`:

```python
TRANSLATION_KEY = re.compile(r"^(?!.+[_-]{2})(?![_-])[a-z0-9-_]+(?<![_-])$")  # hassfest translation_key_validator


def test_every_profile_has_model_label() -> None:
    for profile in ALL_PROFILES:
        key = profile_option(profile.id)
        assert TRANSLATION_KEY.match(key), key
        assert key in STRINGS["selector"]["profile"]["options"], key
        assert key in ES["selector"]["profile"]["options"], key
```

- [ ] **Step 2:** lint; commit `test(red): brand and model steps`; push y ci-wait → rojo.

- [ ] **Step 3: implementación**

`async_step_user`: `SelectSelector(SelectSelectorConfig(options=[SelectOptionDict(value=b, label=BRAND_TITLES[b])
for b in catalog.brands()], mode=SelectSelectorMode.LIST))`. `async_step_model`: opciones `profile_option(p.id)`
con `translation_key="profile"`; placeholder `{brand}`. Etiquetas de §3.2. Textos de §3.1 y §3.2; los textos en
inglés se traducen de los españoles de la spec.

- [ ] **Step 4:** lint; commit `feat: brand and model steps`; push y ci-wait → verde.

### Tarea 12: `connection` con errores con placeholders, `components` y menú `readings`

**Files:** `adapters/inbound/flow.py:55-137`, textos, `tests/ha/test_config_flow.py`, `tests/unit/test_readings.py`

**Interfaces:**
- Consumes: `select`, `ProbeResult`.
- Produces: `format_readings(profile, selection, result, translations, language) -> str`, agrupado por
  componente; menú `readings` con `["name", "model", "connection"]`.

- [ ] **Step 1: tests que fallan**

```python
async def test_cannot_connect_shows_endpoint(hass, failing_gateway) -> None:
    result = await to_connection(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "10.0.0.9"})
    assert result["errors"] == {"base": "cannot_connect"}
    assert result["description_placeholders"] | {} >= {"host": "10.0.0.9", "port": "502", "timeout": "20"}
    assert "profile" in result["data_schema"].schema  # campo «Modelo» tras el error


async def test_components_step_then_readings_menu(hass) -> None:
    result = await to_components(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": ["battery"]})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["name", "model", "connection"]


async def test_profile_without_components_skips_step(hass) -> None:
    result = await to_connection(hass, profile="ingeteam_oneplay")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "10.0.0.9"})
    assert result["step_id"] == "readings"
```

Los placeholders `host`, `port` y `timeout` van siempre en el paso `connection`, con o sin error. Comprobación
de subconjunto con `.items() >=`. `to_connection`/`to_components`: helpers en el propio fichero de test.

`tests/unit/test_readings.py`: grupos por componente en el orden del perfil, título = nombre traducido del
dispositivo, separador de miles (`1,234` en `en`), sin `binary_sensor`, grupo vacío no aparece, `—` sin valor.

- [ ] **Step 2:** lint; commit `test(red): connection errors, components and readings menu`; push y ci-wait → rojo.

- [ ] **Step 3: implementación** según §3.3, §3.4 y §3.7. Formato de miles con `babel`/`locale` no: usar
  `f"{value:,}"` y cambiar `,` por `.` en `es` (comprobar el resultado en el test). Al volver a `model` se olvidan
  lecturas y componentes; al volver a `connection`, solo las lecturas.

- [ ] **Step 4:** lint; commit `feat: connection errors, components step and readings menu`; push y ci-wait → verde.

### Tarea 13: paso `name` con Device ID y número de serie

**Files:** `adapters/inbound/flow.py:139-155`, textos, `tests/fakes.py`, `tests/ha/test_config_flow.py`

**Interfaces:**
- Produces: `free_device_id(hass, device_type: str, exclude: str | None = None) -> int`;
  `used_device_ids(hass, device_type, exclude) -> set[int]`; `valid_serial(value: str) -> bool`.

- [ ] **Step 1: tests que fallan** — los de spec §12, alta: `test_device_id_defaults_to_lowest_free`,
  `test_device_id_in_use_shows_error`, `test_device_id_free_across_device_types` (perfil falso con
  `device_type="irradiance_sensor"` en `tests/fakes.py`), `test_entries_without_device_id_do_not_block`, y
  `test_invalid_serial_number`:

```python
async def test_device_id_defaults_to_lowest_free(hass) -> None:
    add_entry(hass, device_id=0)
    add_entry(hass, device_id=2, host="10.0.0.2")
    result = await to_name(hass)
    assert suggested(result, "device_id") == 1


async def test_device_id_in_use_shows_error(hass) -> None:
    add_entry(hass, device_id=0)
    result = await to_name(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "x", "device_id": 0})
    assert result["errors"] == {"device_id": "device_id_in_use"}
    assert result["step_id"] == "name"


async def test_invalid_serial_number(hass) -> None:
    result = await to_name(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "x", "device_id": 0, "serial_number": "AB 1"}
    )
    assert result["errors"] == {"serial_number": "invalid_serial_number"}
```

`add_entry` = `MockConfigEntry(domain=DOMAIN, data={…, "device_id": n}).add_to_hass(hass)`; `suggested` lee el
`suggested_value` o el `default` del esquema, según cómo lo ponga la implementación.

- [ ] **Step 2:** lint; commit `test(red): name step with device id and serial`; push y ci-wait → rojo.

- [ ] **Step 3: implementación** según §3.5. `NumberSelector(NumberSelectorConfig(min=0, step=1,
  mode=NumberSelectorMode.BOX))` devuelve `float`: `int()` en el código. Placeholder `device_type` = nombre
  traducido en minúscula. Serie: `value.strip()`, válido si `isalnum()` y ASCII.

- [ ] **Step 4:** lint; commit `feat: name step with device id and serial`; push y ci-wait → verde.

### Tarea 14: paso `intervals`, alta completa y `reconfigure` en tres pasos

**Files:** `adapters/inbound/flow.py:157-205`, textos, `tests/ha/test_config_flow.py`

**Interfaces:**
- Consumes: `request_rate`, `min_tier_interval`, `select`, `free_device_id`.
- Produces: `intervals_schema(profile, selection, defaults, translations) -> vol.Schema`, compartido por
  `intervals` y `reconfigure_intervals`; `entity_list(profile, selection, tier, translations) -> str` (§4.4).

- [ ] **Step 1: tests que fallan**

- `test_add_inverter` (existe): recorre los pasos nuevos y comprueba `data` con `components`, `device_id`,
  `serial_number` (si lo hay) e `intervals == {"instant": 5, "fast": 10, "normal": 60, "slow": 3600}`.
- `test_interval_budget_exceeded` en alta y en reconfigure: `instant` 1 → `errors == {"base":
  "interval_budget_exceeded"}` con placeholder `rate`.
- `test_interval_too_short`: `fast` 5 → error del campo.
- `test_reconfigure_three_steps`: `reconfigure` → `reconfigure_components` → `reconfigure_intervals` → abort
  `reconfigure_successful`; cambia `unit_id`.
- `test_reconfigure_probe_failure_stays`: sonda fallida → mismo paso con `cannot_connect`.
- `test_reconfigure_prefills_device_id`, `test_reconfigure_device_id_excludes_own_entry`,
  `test_reconfigure_same_id_skips_rename` (spec §12).
- Tiers sin entidades no aparecen: `ingeteam.oneplay` no tiene sección `slow` ni `instant`.

- [ ] **Step 2:** lint; commit `test(red): intervals step and three-step reconfigure`; push y ci-wait → rojo.

- [ ] **Step 3: implementación** según §3.6, §4.1-§4.4. Orden de validación: `interval_too_short` y después
  presupuesto. `async_update_reload_and_abort(entry, unique_id=…, data=…)` con `data` completa (sin
  `data_updates`).

- [ ] **Step 4:** lint; commit `feat: intervals step and three-step reconfigure`; push y ci-wait → verde.

### Tarea 15: paso `reconfigure_rename`

**Files:** `adapters/inbound/flow.py`, textos, `tests/ha/test_config_flow.py`

**Interfaces:**
- Produces: `plan_rename(hass, entry, old_id: int | None, new_id: int) -> RenamePlan(renamed: list[tuple[str, str]],
  kept: list[str], collisions: list[str])`; slug con `homeassistant.util.slugify`.

- [ ] **Step 1: tests que fallan** — spec §12, reconfigure: `test_reconfigure_rename_renames_generated_ids`
  (`sensor.battery_0_voltage` → `sensor.battery_2_voltage`, mismo `unique_id`),
  `test_reconfigure_rename_keeps_custom_ids`, `test_reconfigure_rename_skips_collisions`,
  `test_reconfigure_rename_counts_in_placeholders`. En inglés, como en la Tarea 9.

- [ ] **Step 2:** lint; commit `test(red): reconfigure rename step`; push y ci-wait → rojo.

- [ ] **Step 3: implementación** según §4.5: prefijo `<plataforma>.<slugify(nombre traducido del dispositivo con
  el ID guardado)>_`; renombrar con `er.async_get(hass).async_update_entity(entity_id, new_entity_id=…)` y después
  `async_update_reload_and_abort`.

- [ ] **Step 4:** lint; commit `feat: reconfigure rename step`; push y ci-wait → verde. Revisión final de textos:
  `grep -in "entry\|host\|endpoint\|inversor" strings.json translations/es.json` solo deja nombres de componente
  y claves.

---

### Tarea 16: sync de documentación (`project-docs` modo sync)

Las citas `archivo:línea` de los documentos vivos se sacan de la rama ya implementada: `graft grep "<símbolo>"` o
`grep -n`. No se copian de este plan.

- [ ] ADR nuevo `docs/decisions/0016-instant-tier.md`: tier `instant` y presupuesto de una petición por segundo.
- [ ] `docs/decisions/0005-poll-tiers.md`: `fast` 10 s por defecto; enlace al 0016.
- [ ] `docs/features/device-setup.md:90` y el resto del fichero: flujo nuevo, 10 s.
- [ ] Wiki del modelo (`:21`, «fast 5 s» → 10 s; 30070-30072 en `instant`).
- [ ] `docs/architecture/`: selección por componentes, dispositivos por componente, `binary_sensor`.
- [ ] `CHANGELOG.md` y `README.md`.
- [ ] `spec.md` y este `plan.md`: `status: done`.
- [ ] lint; commit `docs: setup flow v2 sync`; push y ci-wait → verde.

---

## Auto-revisión

### Cobertura de la spec

| Spec | Tarea |
|---|---|
| §3.1 marca, test brand = carpeta | 11, 7 |
| §3.2 modelo y etiquetas | 11 |
| §3.3 conexión, errores, campo «Modelo» | 12 |
| §3.4 menú y `format_readings` | 12 |
| §3.5 nombre, Device ID, serie | 13 |
| §3.6 intervalos del alta | 14 |
| §3.7 componentes | 12 |
| §3.8 serie por Modbus | 2, 6, 9 |
| §4.1-§4.4 reconfigure | 14 |
| §4.5 renombrado | 15 |
| §5.1 dominio de componentes | 4, 5, 7 |
| §5.2 dispositivos, `hub` | 9 |
| §5.3 bits del BMS | 3, 7, 10 |
| §5.4 nombres cortos | 7 |
| §5.5 runtime y registro | 8 |
| §5.6 Device ID | 9, 13, 15 |
| §5.7 tiers de las extras | 7 |
| §5.8 tier `instant` y presupuesto | 1, 6 |
| §6 textos | 1, 7, 9, 11-15 |
| §8 compatibilidad | 8, 9 |
| §12 tests del Device ID | 9, 13, 14, 15 |
| Docs | 16 |

### Decisiones del plan que ajustan la spec

- `slow` = 3 bloques (3.0 s), no 4: la spec cuenta 30043 de `reason-labels`, que no está en esta rama.
- Rama propia `feat/setup-flow-v2` con base `main`, en un worktree hijo de Orca (Tarea 0).
- Clave del selector de modelo: id con `_` en lugar de `.` (`ingeteam_oneplay_storage`), como clave y `value`, por
  la regex de hassfest `translation_key_validator`. Lo comprueba un test (Tarea 11).
- Texto ASCII: `DataType.ASCII`, `RegisterSpec.length` y `RegisterSpec.words`; `DataType.words` lanza `ValueError`
  con ASCII; `decode_text` aparte de `decode`; validate exige `serial` ASCII con `length ≥ 1` y prohíbe ASCII en
  entidades.
- `select(profile, components)` en `application/selection.py`; `None` = todos los opcionales.
- `request_rate(profile, intervals)` en `poller.py`.
- `ProbeResult(readings, serial)`: `readings` = `fast` + `instant`.
- Los textos en inglés se traducen de los españoles de la spec.
- Tests de HA en inglés: «Battery 0», `sensor.battery_0_voltage` en lugar de los ejemplos en español de la spec.
- Test de restauración de energía con `suggested_object_id="inverter_solar_energy"` en el registro.
- Placeholders `host`, `port` y `timeout` siempre presentes en `connection`.

### Tipos coherentes entre tareas

`PollTier.INSTANT`, `Component`, `ComponentSpec`, `Selection`/`select`, `request_rate`, `ProbeResult`,
`decode_text`, `RegisterSpec.words`, `CONF_COMPONENTS`/`CONF_DEVICE_ID`/`CONF_SERIAL_NUMBER`, `device_info`,
`profile_option`, `free_device_id`, `intervals_schema`, `entity_list`, `plan_rename`: definidos una vez y usados
con la misma firma.

### Sin marcadores pendientes

Sin TBD ni TODO. Los puntos que dependen del código real (nombres de helpers de test, textos exactos de errores
ya existentes, firma de `_extra`) llevan la orden de comprobarlos con `grep` y de avisar si difieren.
