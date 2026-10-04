---
type: feature
area: core
layers: [domain, application, ports, adapters, profiles]
status: draft
date: 2026-10-04
---

# Plan de implementación — Spec 0, esqueleto de `modbus_solar`

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `subagent-driven-development` (recomendada) o
> `executing-plans` para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** construir la custom integration `modbus_solar` (capas hexagonales, config flow
marca + equipo, 3 sensores del Ingeteam 1Play Storage, diagnostics, CI y empaquetado HACS)
según `docs/changes/2026-10-04-skeleton/spec.md`.

**Arquitectura:** núcleo puro (`domain`, `ports`, `application`, `profiles`) sin Home Assistant
ni `modbus_connection`, verificado con import-linter. Los adaptadores de entrada (flows,
coordinators, entidades, diagnostics) y de salida (`ModbusGateway`) se conectan solo en las
raíces de composición `__init__.py` y `config_flow.py`.

**Stack:** Python 3.14, Home Assistant 2026.9.4 (mínimo 2026.9.0), `modbus-connection` 4.10.0
(vía la integración `modbus` del core), pytest + `pytest-homeassistant-custom-component`
0.13.367, ruff, import-linter, GitHub Actions, HACS.

## Global Constraints

- Rama de trabajo: `feat/skeleton`, creada desde `docs/architecture-analysis`. Nunca commit en `main`.
- Push a `feat/skeleton` autorizado sin confirmar. Force push, merge y rebase piden confirmación.
- **Tests solo en GitHub Actions.** Nunca `pytest` en la máquina Windows. RED y GREEN se
  comprueban con `bash scripts/ci-wait.sh` (Tarea 1), lanzado con `run_in_background: true`
  en la herramienta Bash: el script espera con `sleep`.
- Gates locales antes de cada commit: `bash scripts/lint.sh` (ruff format, ruff check,
  import-linter, compileall). No ejecuta tests.
- Commits RED (`test(red): …`) se permiten en `feat/skeleton`: son el paso RED del TDD en CI.
  Un commit GREEN por tarea con gates y CI en verde.
- Todo commit termina con:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5
  ```
- Comentarios del código en español. Todo lo demás en inglés: ficheros, identificadores,
  mensajes de log y de excepción, textos de `strings.json`.
- Ficheros en `snake_case` (estándar de Python). Funciones y variables `snake_case`, clases
  `PascalCase`, constantes `UPPER_SNAKE_CASE`.
- Dentro de `custom_components/modbus_solar` solo imports relativos (`from ..domain import …`).
  Los tests importan `custom_components.modbus_solar.…`.
- ruff: `target-version = "py314"`, `line-length = 120`, `select = ["E", "F", "I", "UP", "B"]`.
- Pines del job `test`: `pytest-homeassistant-custom-component==0.13.367`, `pymodbus==3.13.1`,
  `modbus-connection[tmodbus]==4.10.0`, `tmodbus==0.6.2`.
- `hacs.json`: `"homeassistant": "2026.9.0"`. `manifest.json`: `"version": "0.1.0"`.
- Intervalos por defecto: `fast` 5 s, `normal` 60 s, `slow` 3600 s.
- Identificadores estables: device `(DOMAIN, subentry_id)`; entidad `f"{subentry_id}_{key}"`;
  subentry `f"{host.lower()}:{port}:{unit_id}"`; dispositivo de marca `(DOMAIN, entry_id)`.
- `graft/` y `.graft_*` nunca se commitean.
- No inventar: si una API no se comporta como dice el plan, parar y avisar con la salida real.

## Mapa de ficheros

```
.gitignore  pyproject.toml  hacs.json  README.md
scripts/lint.sh  scripts/ci-wait.sh
.github/workflows/tests.yml  validate.yml  release.yml
custom_components/modbus_solar/
  __init__.py  config_flow.py  diagnostics.py  sensor.py  const.py
  manifest.json  strings.json  translations/en.json  translations/es.json  brand/icon.png
  domain/__init__.py  types.py  profile.py  errors.py  decode.py  blocks.py  validate.py
  ports/__init__.py  device.py
  application/__init__.py  poller.py  probe.py  catalog.py
  adapters/__init__.py
  adapters/inbound/__init__.py  flow.py  coordinator.py  runtime.py  diagnostics.py
  adapters/inbound/entities/__init__.py  base.py  factory.py
  adapters/outbound/__init__.py  modbus_gateway.py
  profiles/__init__.py  profiles/ingeteam/__init__.py  profiles/ingeteam/oneplay_storage.py
tests/__init__.py  tests/fakes.py
tests/unit/__init__.py  test_packaging.py  test_types.py  test_decode.py  test_blocks.py
  test_validate.py  test_profiles.py  test_poller.py  test_probe.py  test_modbus_gateway.py
  test_unique_ids.py  test_translations.py
tests/ha/__init__.py  conftest.py  common.py  test_coordinator.py  test_init.py  test_sensor.py
  test_config_flow.py  test_subentry_flow.py  test_diagnostics.py
docs/README.md  docs/architecture/…  docs/decisions/0001…0008  docs/guides/…
docs/features/…  docs/wiki/brands/ingeteam/…
```

Responsabilidades: `domain` define tipos, perfil, decodificación, bloques y validación;
`ports` el protocolo `DeviceGateway`; `application` las funciones de caso de uso;
`profiles` los datos de cada equipo; `adapters/inbound` todo lo que habla con HA;
`adapters/outbound` todo lo que habla con `modbus_connection`.

---

### Tarea 1: Scaffolding, gates locales y CI

**Files:**
- Create: `.gitignore`, `pyproject.toml`, `scripts/lint.sh`, `scripts/ci-wait.sh`,
  `.github/workflows/tests.yml`
- Create: `custom_components/modbus_solar/{domain,ports,application,adapters,adapters/inbound,adapters/inbound/entities,adapters/outbound,profiles}/__init__.py`
- Create: `custom_components/modbus_solar/__init__.py`, `const.py`, `manifest.json`
- Test: `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/test_packaging.py`

**Interfaces:**
- Produces: `const.py` con `DOMAIN = "modbus_solar"`, `CONF_BRAND = "brand"`,
  `CONF_PROFILE = "profile"`, `CONF_UNIT_ID = "unit_id"`, `CONF_INTERVALS = "intervals"`,
  `SUBENTRY_DEVICE = "device"`, `DEFAULT_INTERVALS: dict[str, int]`, `BRAND_TITLES: dict[str, str]`.
- Produces: `bash scripts/lint.sh` (gates locales) y `bash scripts/ci-wait.sh [workflow]`
  (push + espera del run; sale con su código).

- [ ] **Paso 1: Rama y entorno local de lint**

```bash
cd /c/Users/carlo/orca/ingeteam-inverter
git switch -c feat/skeleton
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -q ruff import-linter
```

- [ ] **Paso 2: Ficheros de proyecto**

`.gitignore`:

```gitignore
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/

# graft
graft/
.graft_*
```

`pyproject.toml`:

```toml
[tool.ruff]
target-version = "py314"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

# Se ejecuta desde custom_components/ (namespace package sin __init__.py): ver spec §3.2
[tool.importlinter]
root_package = "modbus_solar"
include_external_packages = true

[[tool.importlinter.contracts]]
name = "Hexagonal layers"
type = "layers"
layers = [
    "modbus_solar.adapters",
    "modbus_solar.application",
    "modbus_solar.ports",
    "modbus_solar.domain",
]

[[tool.importlinter.contracts]]
name = "Core does not import Home Assistant or Modbus"
type = "forbidden"
source_modules = [
    "modbus_solar.domain",
    "modbus_solar.ports",
    "modbus_solar.application",
    "modbus_solar.profiles",
]
forbidden_modules = ["homeassistant", "modbus_connection"]

[[tool.importlinter.contracts]]
name = "Profiles only import domain"
type = "forbidden"
source_modules = ["modbus_solar.profiles"]
forbidden_modules = ["modbus_solar.ports", "modbus_solar.application", "modbus_solar.adapters"]

[[tool.importlinter.contracts]]
name = "Core does not know concrete profiles"
type = "forbidden"
source_modules = ["modbus_solar.domain", "modbus_solar.ports", "modbus_solar.application"]
forbidden_modules = ["modbus_solar.profiles"]

[[tool.importlinter.contracts]]
name = "Inbound and outbound adapters are independent"
type = "independence"
modules = ["modbus_solar.adapters.inbound", "modbus_solar.adapters.outbound"]
```

`scripts/lint.sh`:

```bash
#!/usr/bin/env bash
# Gates estáticos locales (sin tests): ruff, import-linter y compileall.
set -eu
cd "$(dirname "$0")/.."
bin=.venv/bin
[ -d .venv/Scripts ] && bin=.venv/Scripts
"$bin/ruff" format .
"$bin/ruff" check .
# import-linter añade el cwd a sys.path: desde custom_components/ encuentra modbus_solar
(cd custom_components && "../$bin/lint-imports" --config ../pyproject.toml)
"$bin/python" -m compileall -q custom_components tests
```

`scripts/ci-wait.sh`:

```bash
#!/usr/bin/env bash
# Empuja HEAD y espera al workflow indicado (por defecto tests.yml) de ese commit.
# Sale con el código del run; si falla, imprime el log de los pasos fallidos.
set -u
workflow="${1:-tests.yml}"
git push -q origin HEAD || exit 1
sha="$(git rev-parse HEAD)"
id=""
for _ in $(seq 1 60); do
  id="$(gh run list --commit "$sha" --workflow "$workflow" --json databaseId -q '.[0].databaseId')"
  [ -n "$id" ] && break
  sleep 5
done
[ -n "$id" ] || { echo "no run of $workflow for $sha"; exit 2; }
gh run watch "$id" --exit-status > /dev/null
status=$?
[ "$status" -ne 0 ] && gh run view "$id" --log-failed | tail -n 80
echo "run $id: exit $status"
exit "$status"
```

`.github/workflows/tests.yml`:

```yaml
name: tests

on:
  push:
    branches: [main, "feat/**", "fix/**", "refactor/**", "docs/**"]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - name: Dependencias
        run: pip install ruff import-linter
      - name: ruff
        run: |
          ruff check .
          ruff format --check .
      - name: import-linter
        working-directory: custom_components
        run: lint-imports --config ../pyproject.toml
      - name: compileall
        run: python -m compileall -q custom_components tests

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - name: Dependencias
        run: >-
          pip install
          "pytest-homeassistant-custom-component==0.13.367"
          "pymodbus==3.13.1"
          "modbus-connection[tmodbus]==4.10.0"
          "tmodbus==0.6.2"
      - name: pytest
        run: pytest
```

Paquetes de capa vacíos. Cada uno de estos ficheros contiene solo su docstring:

| Fichero | Docstring |
|---|---|
| `custom_components/modbus_solar/domain/__init__.py` | `"""Domain: solo stdlib."""` |
| `custom_components/modbus_solar/ports/__init__.py` | `"""Ports: protocolos que implementan los adaptadores de salida."""` |
| `custom_components/modbus_solar/application/__init__.py` | `"""Application: casos de uso sobre domain y ports."""` |
| `custom_components/modbus_solar/adapters/__init__.py` | `"""Adapters: Home Assistant (inbound) y Modbus (outbound)."""` |
| `custom_components/modbus_solar/adapters/inbound/__init__.py` | `"""Adaptadores de entrada: flows, coordinators, entidades, diagnostics."""` |
| `custom_components/modbus_solar/adapters/inbound/entities/__init__.py` | `"""Entidades de Home Assistant."""` |
| `custom_components/modbus_solar/adapters/outbound/__init__.py` | `"""Adaptadores de salida: acceso Modbus."""` |
| `custom_components/modbus_solar/profiles/__init__.py` | `"""Perfiles de equipo: solo domain."""` |
| `custom_components/modbus_solar/__init__.py` | `"""Modbus Solar: raíz de composición."""` |
| `tests/__init__.py`, `tests/unit/__init__.py` | vacío |

- [ ] **Paso 3: Test que falla**

`tests/unit/test_packaging.py`:

```python
"""Manifest coherente con el dominio y con el orden de claves que exige hassfest."""

import json
from pathlib import Path

from custom_components.modbus_solar.const import DOMAIN

PACKAGE = Path(__file__).parents[2] / "custom_components" / "modbus_solar"


def load_manifest() -> dict:
    return json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))


def test_manifest_domain_matches_package() -> None:
    manifest = load_manifest()
    assert manifest["domain"] == DOMAIN == PACKAGE.name


def test_manifest_key_order_for_hassfest() -> None:
    # hassfest: domain, name y el resto en orden alfabético
    keys = list(load_manifest())
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def test_manifest_uses_core_modbus() -> None:
    manifest = load_manifest()
    assert manifest["dependencies"] == ["modbus"]
    assert manifest["requirements"] == []
```

- [ ] **Paso 4: Gates locales, commit RED y CI**

```bash
bash scripts/lint.sh
git add .gitignore pyproject.toml scripts .github custom_components tests
git commit -m "test(red): manifest y dominio del paquete" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
git push -u origin feat/skeleton
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: job `lint` en verde; job `test` en rojo con
`ModuleNotFoundError: No module named 'custom_components.modbus_solar.const'`.

- [ ] **Paso 5: Comprobar que import-linter detecta una violación**

```bash
echo "import homeassistant" > custom_components/modbus_solar/domain/violation.py
bash scripts/lint.sh; echo "exit=$?"
rm custom_components/modbus_solar/domain/violation.py
```

Esperado: `Core does not import Home Assistant or Modbus BROKEN` y `exit=1`. Tras borrar el
fichero, `bash scripts/lint.sh` sale con 0.

- [ ] **Paso 6: Implementación mínima**

`custom_components/modbus_solar/const.py`:

```python
"""Constantes de la integración y claves de configuración."""

DOMAIN = "modbus_solar"

CONF_BRAND = "brand"
CONF_PROFILE = "profile"
CONF_UNIT_ID = "unit_id"
CONF_INTERVALS = "intervals"

SUBENTRY_DEVICE = "device"

# segundos por tier; editables en el reconfigure de cada equipo
DEFAULT_INTERVALS = {"fast": 5, "normal": 60, "slow": 3600}

BRAND_TITLES = {"ingeteam": "Ingeteam"}
```

`custom_components/modbus_solar/manifest.json`:

```json
{
  "domain": "modbus_solar",
  "name": "Modbus Solar",
  "codeowners": ["@Carlosjcfr"],
  "config_flow": true,
  "dependencies": ["modbus"],
  "documentation": "https://github.com/sigergy/modbus-solar-inverter",
  "integration_type": "hub",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/sigergy/modbus-solar-inverter/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

- [ ] **Paso 7: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/const.py custom_components/modbus_solar/manifest.json
git commit -m "feat: scaffolding del paquete modbus_solar, contratos de capas y CI" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `run …: exit 0`; `lint` y `test` en verde (3 tests).

---

### Tarea 2: Tipos de dominio, perfil y errores

**Files:**
- Create: `custom_components/modbus_solar/domain/types.py`, `profile.py`, `errors.py`
- Test: `tests/unit/test_types.py`

**Interfaces:**
- Produces (`domain/types.py`): StrEnums `DataType` (`U16="u16"`, `S16="s16"`, `U32="u32"`,
  `S32="s32"`; propiedades `words: int`, `signed: bool`), `RegisterKind` (`HOLDING="holding"`,
  `INPUT="input"`), `PollTier` (`FAST="fast"`, `NORMAL="normal"`, `SLOW="slow"`), `Role`
  (`INVERTER_STATE="inverter_state"`, `AC_POWER="ac_power"`,
  `ENERGY_PRODUCED_TOTAL="energy_produced_total"`), `Platform` (`SENSOR="sensor"`),
  `WordOrder` (`BIG="big"`, `LITTLE="little"`).
- Produces (`domain/profile.py`): dataclasses congeladas `RegisterSpec`, `EntitySpec`,
  `DeviceProfile` con los campos de la spec §3.3.
- Produces (`domain/errors.py`): `DeviceUnavailable`, `DeviceProtocolError`, `DecodeError`,
  `EndpointInUse` (subclases de `Exception`, independientes entre sí).

- [ ] **Paso 1: Test que falla**

`tests/unit/test_types.py`:

```python
"""Tipos del dominio: tamaños, valores y dataclasses congeladas."""

import dataclasses

import pytest

from custom_components.modbus_solar.domain.errors import (
    DecodeError,
    DeviceProtocolError,
    DeviceUnavailable,
    EndpointInUse,
)
from custom_components.modbus_solar.domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from custom_components.modbus_solar.domain.types import (
    DataType,
    Platform,
    PollTier,
    RegisterKind,
    Role,
    WordOrder,
)


def test_data_type_words_and_sign() -> None:
    assert [(t.value, t.words, t.signed) for t in DataType] == [
        ("u16", 1, False),
        ("s16", 1, True),
        ("u32", 2, False),
        ("s32", 2, True),
    ]


def test_enum_values_are_stable() -> None:
    # se guardan en config entries y en diagnostics: cambiarlos rompe instalaciones
    assert [t.value for t in PollTier] == ["fast", "normal", "slow"]
    assert [k.value for k in RegisterKind] == ["holding", "input"]
    assert [w.value for w in WordOrder] == ["big", "little"]
    assert [p.value for p in Platform] == ["sensor"]
    assert [r.value for r in Role] == ["inverter_state", "ac_power", "energy_produced_total"]


def test_register_spec_defaults() -> None:
    reg = RegisterSpec(address=0x1021, dtype=DataType.U32)
    assert reg.kind is RegisterKind.HOLDING
    assert (reg.scale, reg.offset, reg.word_order) == (1.0, 0.0, WordOrder.BIG)


def test_register_spec_is_frozen_and_hashable() -> None:
    # el gateway devuelve las palabras con el RegisterSpec como clave
    reg = RegisterSpec(address=1, dtype=DataType.U16)
    assert {reg: "x"}[RegisterSpec(address=1, dtype=DataType.U16)] == "x"
    with pytest.raises(dataclasses.FrozenInstanceError):
        reg.address = 2  # type: ignore[misc]


def test_entity_spec_defaults() -> None:
    spec = EntitySpec(
        key="k",
        role=Role.AC_POWER,
        platform=Platform.SENSOR,
        register=RegisterSpec(address=1, dtype=DataType.U16),
        poll=PollTier.FAST,
    )
    assert (spec.device_class, spec.state_class, spec.unit, spec.enum) == (None, None, None, None)
    assert spec.entity_category is None
    assert spec.enabled_default is True


def test_profile_default_block_limit_is_fc03_maximum() -> None:
    profile = DeviceProfile(
        id="test.device",
        brand="test",
        device_type="inverter",
        models=("M",),
        min_request_interval_s=1.0,
        default_port=502,
        default_unit_id=1,
        probe_key="k",
        entities=(),
    )
    assert profile.max_block_registers == 125


DOMAIN_ERRORS = {DeviceUnavailable, DeviceProtocolError, DecodeError, EndpointInUse}


@pytest.mark.parametrize("error", sorted(DOMAIN_ERRORS, key=lambda e: e.__name__))
def test_domain_errors_are_independent(error: type[Exception]) -> None:
    others = DOMAIN_ERRORS - {error}
    assert issubclass(error, Exception)
    assert not any(issubclass(error, other) for other in others)
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_types.py
git commit -m "test(red): tipos, perfil y errores del dominio" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.domain.errors'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/domain/types.py`:

```python
"""Enumeraciones del dominio. Sus valores se guardan en config y diagnostics: no cambiarlos."""

from enum import StrEnum


class DataType(StrEnum):
    U16 = "u16"
    S16 = "s16"
    U32 = "u32"
    S32 = "s32"

    @property
    def words(self) -> int:
        """Número de registros de 16 bits que ocupa."""
        return 1 if self in (DataType.U16, DataType.S16) else 2

    @property
    def signed(self) -> bool:
        return self in (DataType.S16, DataType.S32)


class RegisterKind(StrEnum):
    HOLDING = "holding"
    INPUT = "input"


class PollTier(StrEnum):
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"


class Role(StrEnum):
    """Significado semántico de la entidad, independiente de la marca (lo usará el frontend)."""

    INVERTER_STATE = "inverter_state"
    AC_POWER = "ac_power"
    ENERGY_PRODUCED_TOTAL = "energy_produced_total"


class Platform(StrEnum):
    SENSOR = "sensor"


class WordOrder(StrEnum):
    """Orden de las palabras en tipos de 32 bits: big = palabra alta primero."""

    BIG = "big"
    LITTLE = "little"
```

`custom_components/modbus_solar/domain/profile.py`:

```python
"""Modelo de perfil de equipo: registros, entidades y parámetros de comunicación."""

from collections.abc import Mapping
from dataclasses import dataclass

from .types import DataType, Platform, PollTier, RegisterKind, Role, WordOrder


@dataclass(frozen=True, kw_only=True)
class RegisterSpec:
    address: int
    kind: RegisterKind = RegisterKind.HOLDING
    dtype: DataType
    scale: float = 1.0
    offset: float = 0.0
    word_order: WordOrder = WordOrder.BIG


@dataclass(frozen=True, kw_only=True)
class EntitySpec:
    key: str  # también translation_key y sufijo del unique_id
    role: Role
    platform: Platform
    register: RegisterSpec
    poll: PollTier
    device_class: str | None = None  # cadenas: domain no importa HA
    state_class: str | None = None
    unit: str | None = None
    enum: Mapping[int, str] | None = None
    entity_category: str | None = None
    enabled_default: bool = True


@dataclass(frozen=True, kw_only=True)
class DeviceProfile:
    id: str
    brand: str
    device_type: str
    models: tuple[str, ...]
    min_request_interval_s: float
    max_block_registers: int = 125  # 125 = límite de FC03/FC04
    default_port: int
    default_unit_id: int
    probe_key: str  # entidad que lee el config flow para validar el equipo
    entities: tuple[EntitySpec, ...]
```

`custom_components/modbus_solar/domain/errors.py`:

```python
"""Errores del dominio. Solo el gateway conoce las excepciones de modbus_connection."""


class DeviceUnavailable(Exception):
    """El equipo no responde: sin conexión o tiempo agotado."""


class DeviceProtocolError(Exception):
    """El equipo responde con una excepción Modbus o una trama inválida."""


class DecodeError(Exception):
    """Las palabras leídas no dan un valor válido para la entidad."""


class EndpointInUse(Exception):
    """El endpoint ya está abierto con otros parámetros de enlace."""
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/domain
git commit -m "feat(domain): tipos, perfil y errores" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 3: `decode`

**Files:**
- Create: `custom_components/modbus_solar/domain/decode.py`
- Test: `tests/unit/test_decode.py`

**Interfaces:**
- Consumes: `EntitySpec`, `RegisterSpec`, `DataType`, `WordOrder`, `DecodeError` (Tarea 2).
- Produces: `decode(entity: EntitySpec, words: Sequence[int]) -> int | float | str`. Devuelve
  `int` sin escala ni offset, `float` redondeado a 6 decimales con ellos, `str` con `enum`.
  Lanza `DecodeError` si el número de palabras no cuadra, si una palabra sale de 0..0xFFFF o
  si el valor no está en el `enum`.

- [ ] **Paso 1: Test que falla**

`tests/unit/test_decode.py`:

```python
"""Decodificación de palabras Modbus a valor de entidad."""

from collections.abc import Mapping

import pytest

from custom_components.modbus_solar.domain.decode import decode
from custom_components.modbus_solar.domain.errors import DecodeError
from custom_components.modbus_solar.domain.profile import EntitySpec, RegisterSpec
from custom_components.modbus_solar.domain.types import DataType, Platform, PollTier, Role, WordOrder


def entity(
    dtype: DataType,
    *,
    word_order: WordOrder = WordOrder.BIG,
    scale: float = 1.0,
    offset: float = 0.0,
    enum: Mapping[int, str] | None = None,
) -> EntitySpec:
    return EntitySpec(
        key="k",
        role=Role.AC_POWER,
        platform=Platform.SENSOR,
        poll=PollTier.FAST,
        register=RegisterSpec(address=0, dtype=dtype, scale=scale, offset=offset, word_order=word_order),
        device_class="enum" if enum else None,
        enum=enum,
    )


@pytest.mark.parametrize(
    ("dtype", "words", "expected"),
    [
        (DataType.U16, (0xFFFF,), 65535),
        (DataType.S16, (0xFFFF,), -1),
        (DataType.S16, (0x7FFF,), 32767),
        (DataType.U32, (0x0001, 0x0002), 65538),
        (DataType.S32, (0xFFFF, 0xFFFE), -2),
        (DataType.S32, (0x0000, 0x3039), 12345),
    ],
)
def test_integers_with_high_word_first(dtype: DataType, words: tuple[int, ...], expected: int) -> None:
    value = decode(entity(dtype), words)
    assert value == expected
    assert type(value) is int


def test_little_word_order_swaps_words() -> None:
    assert decode(entity(DataType.U32, word_order=WordOrder.LITTLE), (0x0002, 0x0001)) == 65538


def test_scale_and_offset() -> None:
    assert decode(entity(DataType.S32, scale=0.1), (0, 12345)) == 1234.5
    assert decode(entity(DataType.U16, scale=0.1, offset=-40.0), (500,)) == 10.0


def test_float_noise_is_rounded() -> None:
    # 3 * 0.1 = 0.30000000000000004 sin redondeo
    assert decode(entity(DataType.U16, scale=0.1), (3,)) == 0.3


def test_enum_maps_raw_value() -> None:
    assert decode(entity(DataType.U16, enum={3: "grid_connected"}), (3,)) == "grid_connected"


def test_value_outside_enum_raises() -> None:
    with pytest.raises(DecodeError, match="7"):
        decode(entity(DataType.U16, enum={3: "grid_connected"}), (7,))


def test_wrong_word_count_raises() -> None:
    with pytest.raises(DecodeError, match="expected 2 words"):
        decode(entity(DataType.U32), (1,))


def test_word_out_of_range_raises() -> None:
    with pytest.raises(DecodeError, match="out of range"):
        decode(entity(DataType.U16), (0x10000,))
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_decode.py
git commit -m "test(red): decode de palabras Modbus" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.domain.decode'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/domain/decode.py`:

```python
"""Palabras de 16 bits -> valor de la entidad (entero, real escalado o estado de enum)."""

from collections.abc import Sequence

from .errors import DecodeError
from .profile import EntitySpec
from .types import WordOrder


def decode(entity: EntitySpec, words: Sequence[int]) -> int | float | str:
    reg = entity.register
    count = reg.dtype.words
    if len(words) != count:
        raise DecodeError(f"{entity.key}: expected {count} words, got {len(words)}")
    for word in words:
        if not 0 <= word <= 0xFFFF:
            raise DecodeError(f"{entity.key}: word out of range: {word}")

    ordered = list(words) if reg.word_order is WordOrder.BIG else list(reversed(words))
    raw = 0
    for word in ordered:
        raw = (raw << 16) | word
    bits = 16 * count
    if reg.dtype.signed and raw >= 1 << (bits - 1):
        raw -= 1 << bits

    if entity.enum is not None:
        if raw not in entity.enum:
            raise DecodeError(f"{entity.key}: value {raw} not in enum")
        return entity.enum[raw]
    if reg.scale == 1 and reg.offset == 0:
        return raw
    # el redondeo quita el ruido de coma flotante de la escala (3 * 0.1)
    return round(raw * reg.scale + reg.offset, 6)
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/domain/decode.py
git commit -m "feat(domain): decode de enteros, escala, offset y enum" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 4: `plan_blocks`

**Files:**
- Create: `custom_components/modbus_solar/domain/blocks.py`
- Test: `tests/unit/test_blocks.py`

**Interfaces:**
- Consumes: `RegisterSpec`, `RegisterKind`, `DataType.words` (Tarea 2).
- Produces: `Block(kind: RegisterKind, address: int, count: int)` (dataclass congelada,
  posicional) y `plan_blocks(registers: Iterable[RegisterSpec], max_gap: int, max_count: int) -> list[Block]`.
  Ordena por `(kind, address)` y quita duplicados. Nunca mezcla `kind`, nunca parte un
  registro de 32 bits y nunca supera `max_count` registros por bloque.

- [ ] **Paso 1: Test que falla**

`tests/unit/test_blocks.py`:

```python
"""Agrupado de registros en bloques de lectura."""

from custom_components.modbus_solar.domain.blocks import Block, plan_blocks
from custom_components.modbus_solar.domain.profile import RegisterSpec
from custom_components.modbus_solar.domain.types import DataType, RegisterKind

HOLDING = RegisterKind.HOLDING
INPUT = RegisterKind.INPUT


def reg(address: int, dtype: DataType = DataType.U16, kind: RegisterKind = HOLDING) -> RegisterSpec:
    return RegisterSpec(address=address, dtype=dtype, kind=kind)


def test_empty() -> None:
    assert plan_blocks([], 0, 125) == []


def test_contiguous_registers_share_block() -> None:
    assert plan_blocks([reg(10), reg(11, DataType.U32)], 0, 125) == [Block(HOLDING, 10, 3)]


def test_gap_splits_with_zero_max_gap() -> None:
    assert plan_blocks([reg(10), reg(12)], 0, 125) == [Block(HOLDING, 10, 1), Block(HOLDING, 12, 1)]


def test_gap_within_max_gap_is_read_through() -> None:
    assert plan_blocks([reg(10), reg(12)], 1, 125) == [Block(HOLDING, 10, 3)]


def test_block_never_exceeds_max_count() -> None:
    blocks = plan_blocks([reg(a) for a in range(5)], 0, 2)
    assert blocks == [Block(HOLDING, 0, 2), Block(HOLDING, 2, 2), Block(HOLDING, 4, 1)]


def test_32_bit_register_is_not_split() -> None:
    assert plan_blocks([reg(0), reg(1, DataType.U32)], 0, 2) == [Block(HOLDING, 0, 1), Block(HOLDING, 1, 2)]


def test_kinds_never_mix() -> None:
    blocks = plan_blocks([reg(10, kind=INPUT), reg(11)], 0, 125)
    assert blocks == [Block(HOLDING, 11, 1), Block(INPUT, 10, 1)]


def test_unsorted_and_duplicated_input() -> None:
    assert plan_blocks([reg(11), reg(10), reg(10)], 0, 125) == [Block(HOLDING, 10, 2)]


def test_ingeteam_layout_needs_three_blocks() -> None:
    # 0x101D (u16), 0x1021 (u32) y 0x1037 (s32) no son contiguos
    registers = [reg(0x101D), reg(0x1021, DataType.U32), reg(0x1037, DataType.S32)]
    assert plan_blocks(registers, 0, 124) == [
        Block(HOLDING, 0x101D, 1),
        Block(HOLDING, 0x1021, 2),
        Block(HOLDING, 0x1037, 2),
    ]
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_blocks.py
git commit -m "test(red): plan_blocks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.domain.blocks'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/domain/blocks.py`:

```python
"""Agrupado de registros en bloques de lectura Modbus (una petición por bloque)."""

from collections.abc import Iterable
from dataclasses import dataclass

from .profile import RegisterSpec
from .types import RegisterKind


@dataclass(frozen=True)
class Block:
    kind: RegisterKind
    address: int
    count: int


def plan_blocks(registers: Iterable[RegisterSpec], max_gap: int, max_count: int) -> list[Block]:
    blocks: list[Block] = []
    for reg in sorted(set(registers), key=lambda r: (r.kind, r.address)):
        end = reg.address + reg.dtype.words
        if blocks:
            last = blocks[-1]
            last_end = last.address + last.count
            new_end = max(last_end, end)
            # se fusiona si es del mismo tipo, el hueco cabe en max_gap y el bloque en max_count
            fits = reg.address - last_end <= max_gap and new_end - last.address <= max_count
            if last.kind is reg.kind and fits:
                blocks[-1] = Block(last.kind, last.address, new_end - last.address)
                continue
        blocks.append(Block(reg.kind, reg.address, reg.dtype.words))
    return blocks
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/domain/blocks.py
git commit -m "feat(domain): plan_blocks agrupa registros en bloques de lectura" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 5: `validate_profile`

**Files:**
- Create: `custom_components/modbus_solar/domain/validate.py`
- Test: `tests/unit/test_validate.py`

**Interfaces:**
- Consumes: `DeviceProfile`, `EntitySpec`, `RegisterSpec`, `WordOrder` (Tarea 2).
- Produces: `validate_profile(profile: DeviceProfile) -> list[str]`. Lista vacía si el perfil
  es válido. Mensajes exactos:
  `"duplicate key: {key}"`, `"probe_key missing: {probe_key}"`, `"overlap: {a} and {b}"`,
  `"{key}: enum requires device_class enum"`, `"{key}: device_class enum requires enum"`,
  `"{key}: scale 0"`, `"{key}: word_order {word_order} on 16-bit type"`.

- [ ] **Paso 1: Test que falla**

`tests/unit/test_validate.py`:

```python
"""Reglas de validación de perfiles (spec §3.3)."""

from custom_components.modbus_solar.domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from custom_components.modbus_solar.domain.types import (
    DataType,
    Platform,
    PollTier,
    RegisterKind,
    Role,
    WordOrder,
)
from custom_components.modbus_solar.domain.validate import validate_profile


def ent(
    key: str,
    address: int,
    dtype: DataType = DataType.U16,
    *,
    kind: RegisterKind = RegisterKind.HOLDING,
    scale: float = 1.0,
    word_order: WordOrder = WordOrder.BIG,
    device_class: str | None = None,
    enum: dict[int, str] | None = None,
) -> EntitySpec:
    return EntitySpec(
        key=key,
        role=Role.AC_POWER,
        platform=Platform.SENSOR,
        poll=PollTier.FAST,
        register=RegisterSpec(address=address, dtype=dtype, kind=kind, scale=scale, word_order=word_order),
        device_class=device_class,
        enum=enum,
    )


def profile(*entities: EntitySpec, probe_key: str = "a") -> DeviceProfile:
    return DeviceProfile(
        id="test.device",
        brand="test",
        device_type="inverter",
        models=("M",),
        min_request_interval_s=1.0,
        default_port=502,
        default_unit_id=1,
        probe_key=probe_key,
        entities=entities,
    )


def test_valid_profile_has_no_problems() -> None:
    assert validate_profile(profile(ent("a", 0), ent("b", 1, DataType.U32))) == []


def test_duplicate_key() -> None:
    assert validate_profile(profile(ent("a", 0), ent("a", 5))) == ["duplicate key: a"]


def test_probe_key_missing() -> None:
    assert validate_profile(profile(ent("a", 0), probe_key="z")) == ["probe_key missing: z"]


def test_overlapping_registers() -> None:
    assert validate_profile(profile(ent("a", 0, DataType.U32), ent("b", 1))) == ["overlap: a and b"]


def test_same_address_in_different_kinds_is_not_overlap() -> None:
    assert validate_profile(profile(ent("a", 0), ent("b", 0, kind=RegisterKind.INPUT))) == []


def test_enum_requires_enum_device_class() -> None:
    assert validate_profile(profile(ent("a", 0, enum={0: "off"}))) == ["a: enum requires device_class enum"]


def test_enum_device_class_requires_enum() -> None:
    assert validate_profile(profile(ent("a", 0, device_class="enum"))) == ["a: device_class enum requires enum"]


def test_scale_zero() -> None:
    assert validate_profile(profile(ent("a", 0, scale=0))) == ["a: scale 0"]


def test_little_word_order_on_16_bit_type() -> None:
    problems = validate_profile(profile(ent("a", 0, word_order=WordOrder.LITTLE)))
    assert problems == ["a: word_order little on 16-bit type"]


def test_little_word_order_on_32_bit_type_is_valid() -> None:
    assert validate_profile(profile(ent("a", 0, DataType.S32, word_order=WordOrder.LITTLE))) == []
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_validate.py
git commit -m "test(red): validate_profile" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.domain.validate'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/domain/validate.py`:

```python
"""Comprobaciones estáticas de un perfil. Lista vacía = perfil válido."""

from itertools import combinations

from .profile import DeviceProfile, RegisterSpec
from .types import WordOrder


def _overlaps(a: RegisterSpec, b: RegisterSpec) -> bool:
    # rangos [address, address + words) del mismo tipo de registro
    return a.kind is b.kind and a.address < b.address + b.dtype.words and b.address < a.address + a.dtype.words


def validate_profile(profile: DeviceProfile) -> list[str]:
    problems: list[str] = []

    seen: set[str] = set()
    for spec in profile.entities:
        if spec.key in seen:
            problems.append(f"duplicate key: {spec.key}")
        seen.add(spec.key)
    if profile.probe_key not in seen:
        problems.append(f"probe_key missing: {profile.probe_key}")

    for a, b in combinations(profile.entities, 2):
        if _overlaps(a.register, b.register):
            problems.append(f"overlap: {a.key} and {b.key}")

    for spec in profile.entities:
        reg = spec.register
        # HA exige options en un sensor enum: van juntos o no van
        if spec.enum is not None and spec.device_class != "enum":
            problems.append(f"{spec.key}: enum requires device_class enum")
        if spec.device_class == "enum" and spec.enum is None:
            problems.append(f"{spec.key}: device_class enum requires enum")
        if reg.scale == 0:
            problems.append(f"{spec.key}: scale 0")
        if reg.dtype.words == 1 and reg.word_order is not WordOrder.BIG:
            problems.append(f"{spec.key}: word_order {reg.word_order} on 16-bit type")
    return problems
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/domain/validate.py
git commit -m "feat(domain): validate_profile" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 6: Perfil Ingeteam 1Play Storage y catálogo

**Files:**
- Create: `custom_components/modbus_solar/profiles/ingeteam/__init__.py`,
  `custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py`,
  `custom_components/modbus_solar/application/catalog.py`
- Modify: `custom_components/modbus_solar/profiles/__init__.py`,
  `custom_components/modbus_solar/__init__.py`
- Test: `tests/unit/test_profiles.py`

**Interfaces:**
- Consumes: tipos y `DeviceProfile` (Tarea 2), `validate_profile` (Tarea 5).
- Produces: `ONEPLAY_STORAGE: DeviceProfile` (`id="ingeteam.oneplay_storage"`) y
  `ALL_PROFILES: tuple[DeviceProfile, ...]` en `profiles/__init__.py`.
- Produces: `Catalog(profiles: Iterable[DeviceProfile])` con `brands() -> list[str]`,
  `for_brand(brand: str) -> list[DeviceProfile]` y `get(profile_id: str) -> DeviceProfile`
  (`KeyError` si no existe; `ValueError("duplicate profile id: …")` al construir con ids repetidos).
- Produces: `CATALOG = Catalog(ALL_PROFILES)` en `custom_components/modbus_solar/__init__.py`.

Datos del perfil (spec §2; PDF ACL2010IMB05, ES págs. 4-5 y Nota 3 pág. 7):

| Clave | Dirección | Tipo | `scale` | Unidad | `device_class` | `state_class` | Tier | `Role` |
|---|---|---|---|---|---|---|---|---|
| `inverter_state` | `0x101D` | U16 | 1 | — | `enum` | — | `fast` | `INVERTER_STATE` |
| `active_power` | `0x1037` | S32 | 0.1 | `W` | `power` | `measurement` | `fast` | `AC_POWER` |
| `total_energy` | `0x1021` | U32 | 0.1 | `Wh` | `energy` | `total_increasing` | `normal` | `ENERGY_PRODUCED_TOTAL` |

- [ ] **Paso 1: Test que falla**

`tests/unit/test_profiles.py`:

```python
"""Perfil Ingeteam 1Play Storage y catálogo de perfiles."""

import pytest

from custom_components.modbus_solar import CATALOG
from custom_components.modbus_solar.application.catalog import Catalog
from custom_components.modbus_solar.domain.types import DataType, PollTier, RegisterKind, Role, WordOrder
from custom_components.modbus_solar.domain.validate import validate_profile
from custom_components.modbus_solar.profiles import ALL_PROFILES
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE


def entity(key: str):
    return next(e for e in ONEPLAY_STORAGE.entities if e.key == key)


def test_all_profiles_are_valid() -> None:
    for profile in ALL_PROFILES:
        assert validate_profile(profile) == [], profile.id


def test_ingeteam_identity_and_limits() -> None:
    p = ONEPLAY_STORAGE
    assert (p.id, p.brand, p.device_type, p.models) == (
        "ingeteam.oneplay_storage",
        "ingeteam",
        "inverter",
        ("1Play Storage",),
    )
    # PDF ACL2010IMB05 pág. 4: de 1 a 124 registros por lectura y >= 1 s entre peticiones
    assert p.max_block_registers == 124
    assert p.min_request_interval_s == 1.0
    assert (p.default_port, p.default_unit_id) == (502, 1)
    assert p.probe_key == "inverter_state"
    assert [e.key for e in p.entities] == ["inverter_state", "active_power", "total_energy"]


def test_all_registers_are_big_endian_holding() -> None:
    for e in ONEPLAY_STORAGE.entities:
        assert (e.register.kind, e.register.word_order, e.register.offset) == (RegisterKind.HOLDING, WordOrder.BIG, 0)


def test_inverter_state() -> None:
    e = entity("inverter_state")
    assert (e.register.address, e.register.dtype, e.register.scale) == (0x101D, DataType.U16, 1.0)
    assert (e.device_class, e.state_class, e.unit) == ("enum", None, None)
    assert (e.poll, e.role) == (PollTier.FAST, Role.INVERTER_STATE)
    # Nota 3 (pág. 7): solo tres estados documentados
    assert dict(e.enum or {}) == {0: "factory_default", 1: "grid_disconnected", 3: "grid_connected"}


def test_active_power() -> None:
    e = entity("active_power")
    assert (e.register.address, e.register.dtype, e.register.scale) == (0x1037, DataType.S32, 0.1)
    assert (e.device_class, e.state_class, e.unit) == ("power", "measurement", "W")
    assert (e.poll, e.role) == (PollTier.FAST, Role.AC_POWER)


def test_total_energy() -> None:
    e = entity("total_energy")
    assert (e.register.address, e.register.dtype, e.register.scale) == (0x1021, DataType.U32, 0.1)
    assert (e.device_class, e.state_class, e.unit) == ("energy", "total_increasing", "Wh")
    assert (e.poll, e.role) == (PollTier.NORMAL, Role.ENERGY_PRODUCED_TOTAL)


def test_catalog_lookup() -> None:
    assert CATALOG.brands() == ["ingeteam"]
    assert CATALOG.for_brand("ingeteam") == [ONEPLAY_STORAGE]
    assert CATALOG.for_brand("other") == []
    assert CATALOG.get("ingeteam.oneplay_storage") is ONEPLAY_STORAGE
    with pytest.raises(KeyError):
        CATALOG.get("missing")


def test_catalog_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="duplicate profile id: ingeteam.oneplay_storage"):
        Catalog([ONEPLAY_STORAGE, ONEPLAY_STORAGE])
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_profiles.py
git commit -m "test(red): perfil Ingeteam y catálogo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ImportError: cannot import name 'CATALOG' from 'custom_components.modbus_solar'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/profiles/ingeteam/__init__.py`:

```python
"""Perfiles de Ingeteam."""
```

`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py`:

```python
"""Ingeteam 1Play Storage. Fuente: PDF ACL2010IMB05 (docs/wiki/brands/ingeteam/1-play-tl-m/)."""

from ...domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from ...domain.types import DataType, Platform, PollTier, Role

ONEPLAY_STORAGE = DeviceProfile(
    id="ingeteam.oneplay_storage",
    brand="ingeteam",
    device_type="inverter",
    models=("1Play Storage",),
    # pág. 4: periodo entre peticiones >= 1 s y de 1 a 124 registros por lectura (FC03)
    min_request_interval_s=1.0,
    max_block_registers=124,
    default_port=502,
    default_unit_id=1,
    probe_key="inverter_state",
    entities=(
        EntitySpec(
            key="inverter_state",
            role=Role.INVERTER_STATE,
            platform=Platform.SENSOR,
            register=RegisterSpec(address=0x101D, dtype=DataType.U16),
            poll=PollTier.FAST,
            device_class="enum",
            # Nota 3 (pág. 7): solo estos tres estados están documentados
            enum={0: "factory_default", 1: "grid_disconnected", 3: "grid_connected"},
        ),
        EntitySpec(
            key="active_power",
            role=Role.AC_POWER,
            platform=Platform.SENSOR,
            # [W x 10] según el PDF: scale 0.1 sin verificar en equipo; se comprueba con diagnostics
            register=RegisterSpec(address=0x1037, dtype=DataType.S32, scale=0.1),
            poll=PollTier.FAST,
            device_class="power",
            state_class="measurement",
            unit="W",
        ),
        EntitySpec(
            key="total_energy",
            role=Role.ENERGY_PRODUCED_TOTAL,
            platform=Platform.SENSOR,
            # [Wh x 10] según el PDF: scale 0.1 sin verificar en equipo; se comprueba con diagnostics
            register=RegisterSpec(address=0x1021, dtype=DataType.U32, scale=0.1),
            poll=PollTier.NORMAL,
            device_class="energy",
            state_class="total_increasing",
            unit="Wh",
        ),
    ),
)
```

`custom_components/modbus_solar/profiles/__init__.py` (sustituye el contenido):

```python
"""Perfiles de equipo: solo importan domain."""

from ..domain.profile import DeviceProfile
from .ingeteam.oneplay_storage import ONEPLAY_STORAGE

ALL_PROFILES: tuple[DeviceProfile, ...] = (ONEPLAY_STORAGE,)
```

`custom_components/modbus_solar/application/catalog.py`:

```python
"""Catálogo de perfiles por marca e id. No conoce perfiles concretos: se los inyecta la raíz."""

from collections.abc import Iterable

from ..domain.profile import DeviceProfile


class Catalog:
    def __init__(self, profiles: Iterable[DeviceProfile]) -> None:
        self._by_id: dict[str, DeviceProfile] = {}
        for profile in profiles:
            if profile.id in self._by_id:
                raise ValueError(f"duplicate profile id: {profile.id}")
            self._by_id[profile.id] = profile

    def brands(self) -> list[str]:
        return sorted({p.brand for p in self._by_id.values()})

    def for_brand(self, brand: str) -> list[DeviceProfile]:
        return sorted((p for p in self._by_id.values() if p.brand == brand), key=lambda p: p.id)

    def get(self, profile_id: str) -> DeviceProfile:
        return self._by_id[profile_id]
```

`custom_components/modbus_solar/__init__.py` (sustituye el contenido; la Tarea 11 lo amplía):

```python
"""Modbus Solar: raíz de composición."""

from .application.catalog import Catalog
from .profiles import ALL_PROFILES

CATALOG = Catalog(ALL_PROFILES)
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar
git commit -m "feat(profiles): perfil Ingeteam 1Play Storage y catálogo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`. `lint-imports` sigue en verde porque `profiles` solo importa `domain` y
`application.catalog` no importa `profiles`.

---

### Tarea 7: Puerto `DeviceGateway`, `read_tier` y `min_tier_interval`

**Files:**
- Create: `custom_components/modbus_solar/ports/device.py`,
  `custom_components/modbus_solar/application/poller.py`, `tests/fakes.py`
- Test: `tests/unit/test_poller.py`

**Interfaces:**
- Consumes: `decode` (Tarea 3), `plan_blocks` (Tarea 4), `ONEPLAY_STORAGE` (Tarea 6).
- Produces (`ports/device.py`): `class DeviceGateway(Protocol)` con
  `async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]`.
- Produces (`application/poller.py`):
  - `TierResult`, dataclass congelada con `values: dict[str, int | float | str | None]`,
    `raw: dict[str, tuple[int, ...]]` y `decode_errors: dict[str, str]`. Los tres están vacíos por defecto.
  - `async read_tier(tier: PollTier, gateway: DeviceGateway, profile: DeviceProfile, keys: Collection[str]) -> TierResult`.
  - `min_tier_interval(profile: DeviceProfile, tier: PollTier, max_gap: int = 0) -> float`:
    bloques del tier (todas sus entidades) × `profile.min_request_interval_s`.
    Ingeteam: `fast` 2.0, `normal` 1.0, `slow` 0.0.
- Produces (`tests/fakes.py`):
  - `FakeGateway(words: Mapping[int, tuple[int, ...]], error: Exception | None = None)`, con
    atributos mutables `words`, `error` y `calls: list[tuple[RegisterSpec, ...]]`.
  - `INGETEAM_WORDS = {0x101D: (3,), 0x1021: (0, 50000), 0x1037: (0, 12345)}`, que da
    `grid_connected`, 5000.0 Wh y 1234.5 W.

- [ ] **Paso 1: Doble de pruebas y test que falla**

`tests/fakes.py`:

```python
"""Dobles de prueba compartidos por tests/unit y tests/ha."""

from collections.abc import Mapping, Sequence

from custom_components.modbus_solar.domain.profile import RegisterSpec

# palabras crudas del Ingeteam por dirección: grid_connected, 5000.0 Wh y 1234.5 W
INGETEAM_WORDS: dict[int, tuple[int, ...]] = {0x101D: (3,), 0x1021: (0, 50000), 0x1037: (0, 12345)}


class FakeGateway:
    """DeviceGateway en memoria: devuelve `words[address]` o lanza `error`."""

    def __init__(self, words: Mapping[int, tuple[int, ...]], error: Exception | None = None) -> None:
        self.words = dict(words)
        self.error = error
        self.calls: list[tuple[RegisterSpec, ...]] = []

    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]:
        self.calls.append(tuple(specs))
        if self.error is not None:
            raise self.error
        return {spec: self.words[spec.address] for spec in specs}
```

`tests/unit/test_poller.py`:

```python
"""read_tier y min_tier_interval sobre un DeviceGateway falso."""

import pytest

from custom_components.modbus_solar.application.poller import TierResult, min_tier_interval, read_tier
from custom_components.modbus_solar.domain.errors import DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.domain.types import PollTier
from custom_components.modbus_solar.ports.device import DeviceGateway
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE
from tests.fakes import INGETEAM_WORDS, FakeGateway

ALL_KEYS = {"inverter_state", "active_power", "total_energy"}


async def test_reads_and_decodes_only_the_tier() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    result = await read_tier(PollTier.FAST, gateway, ONEPLAY_STORAGE, ALL_KEYS)
    assert result.values == {"inverter_state": "grid_connected", "active_power": 1234.5}
    assert result.raw == {"inverter_state": (3,), "active_power": (0, 12345)}
    assert result.decode_errors == {}
    assert len(gateway.calls) == 1
    assert {spec.address for spec in gateway.calls[0]} == {0x101D, 0x1037}


async def test_keys_outside_selection_are_not_read() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    result = await read_tier(PollTier.FAST, gateway, ONEPLAY_STORAGE, {"inverter_state"})
    assert result.values == {"inverter_state": "grid_connected"}
    assert [spec.address for spec in gateway.calls[0]] == [0x101D]


async def test_no_keys_does_not_call_gateway() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    assert await read_tier(PollTier.SLOW, gateway, ONEPLAY_STORAGE, ALL_KEYS) == TierResult()
    assert await read_tier(PollTier.FAST, gateway, ONEPLAY_STORAGE, set()) == TierResult()
    assert gateway.calls == []


async def test_decode_error_affects_only_its_key() -> None:
    gateway = FakeGateway({**INGETEAM_WORDS, 0x101D: (7,)})
    result = await read_tier(PollTier.FAST, gateway, ONEPLAY_STORAGE, ALL_KEYS)
    assert result.values == {"inverter_state": None, "active_power": 1234.5}
    assert result.raw["inverter_state"] == (7,)
    assert result.decode_errors == {"inverter_state": "inverter_state: value 7 not in enum"}


@pytest.mark.parametrize("error", [DeviceUnavailable("timeout"), DeviceProtocolError("exception 2")])
async def test_gateway_errors_propagate(error: Exception) -> None:
    with pytest.raises(type(error)):
        await read_tier(PollTier.FAST, FakeGateway(INGETEAM_WORDS, error=error), ONEPLAY_STORAGE, ALL_KEYS)


def test_fake_gateway_satisfies_port() -> None:
    gateway: DeviceGateway = FakeGateway(INGETEAM_WORDS)
    assert callable(gateway.read)


@pytest.mark.parametrize(("tier", "expected"), [(PollTier.FAST, 2.0), (PollTier.NORMAL, 1.0), (PollTier.SLOW, 0.0)])
def test_min_tier_interval_for_ingeteam(tier: PollTier, expected: float) -> None:
    # fast: 0x101D y 0x1037 no son contiguos -> 2 bloques x 1.0 s
    assert min_tier_interval(ONEPLAY_STORAGE, tier) == expected
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/fakes.py tests/unit/test_poller.py
git commit -m "test(red): read_tier y min_tier_interval" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.application.poller'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/ports/device.py`:

```python
"""Puerto de salida: lectura de registros de un equipo."""

from collections.abc import Mapping, Sequence
from typing import Protocol

from ..domain.profile import RegisterSpec


class DeviceGateway(Protocol):
    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]:
        """Palabras crudas por registro. Lanza DeviceUnavailable o DeviceProtocolError."""
        ...
```

`custom_components/modbus_solar/application/poller.py`:

```python
"""Lectura de un tier: una llamada al gateway y decodificación por entidad."""

from collections.abc import Collection
from dataclasses import dataclass, field

from ..domain.blocks import plan_blocks
from ..domain.decode import decode
from ..domain.errors import DecodeError
from ..domain.profile import DeviceProfile
from ..domain.types import PollTier
from ..ports.device import DeviceGateway


@dataclass(frozen=True)
class TierResult:
    values: dict[str, int | float | str | None] = field(default_factory=dict)
    raw: dict[str, tuple[int, ...]] = field(default_factory=dict)
    decode_errors: dict[str, str] = field(default_factory=dict)


async def read_tier(
    tier: PollTier,
    gateway: DeviceGateway,
    profile: DeviceProfile,
    keys: Collection[str],
) -> TierResult:
    # keys = entidades habilitadas: no se leen registros de entidades deshabilitadas
    specs = [e for e in profile.entities if e.poll is tier and e.key in keys]
    if not specs:
        return TierResult()
    words = await gateway.read([e.register for e in specs])
    values: dict[str, int | float | str | None] = {}
    raw: dict[str, tuple[int, ...]] = {}
    errors: dict[str, str] = {}
    for spec in specs:
        raw[spec.key] = tuple(words[spec.register])
        try:
            values[spec.key] = decode(spec, raw[spec.key])
        except DecodeError as err:
            # un valor inválido deja la entidad en unknown sin abortar el tier
            values[spec.key] = None
            errors[spec.key] = str(err)
    return TierResult(values=values, raw=raw, decode_errors=errors)


def min_tier_interval(profile: DeviceProfile, tier: PollTier, max_gap: int = 0) -> float:
    """Segundos mínimos para leer el tier entero respetando el espaciado entre peticiones."""
    registers = [e.register for e in profile.entities if e.poll is tier]
    return len(plan_blocks(registers, max_gap, profile.max_block_registers)) * profile.min_request_interval_s
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/ports custom_components/modbus_solar/application
git commit -m "feat(application): puerto DeviceGateway, read_tier y min_tier_interval" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 8: `probe_device`

**Files:**
- Create: `custom_components/modbus_solar/application/probe.py`
- Test: `tests/unit/test_probe.py`

**Interfaces:**
- Consumes: `DeviceGateway` (Tarea 7), `decode` (Tarea 3), `FakeGateway` e `INGETEAM_WORDS` (Tarea 7).
- Produces: `async probe_device(gateway: DeviceGateway, profile: DeviceProfile) -> None`.
  Lee solo el registro de `profile.probe_key` y lo decodifica. Propaga
  `DeviceUnavailable`, `DeviceProtocolError` y `DecodeError`.

- [ ] **Paso 1: Test que falla**

`tests/unit/test_probe.py`:

```python
"""Sonda del config flow: lee y decodifica la entidad probe_key."""

import pytest

from custom_components.modbus_solar.application.probe import probe_device
from custom_components.modbus_solar.domain.errors import DecodeError, DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE
from tests.fakes import INGETEAM_WORDS, FakeGateway


async def test_reads_only_the_probe_register() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    await probe_device(gateway, ONEPLAY_STORAGE)
    assert [[spec.address for spec in call] for call in gateway.calls] == [[0x101D]]


async def test_value_outside_enum_raises_decode_error() -> None:
    with pytest.raises(DecodeError):
        await probe_device(FakeGateway({0x101D: (7,)}), ONEPLAY_STORAGE)


@pytest.mark.parametrize("error", [DeviceUnavailable("timeout"), DeviceProtocolError("exception 2")])
async def test_gateway_errors_propagate(error: Exception) -> None:
    with pytest.raises(type(error)):
        await probe_device(FakeGateway(INGETEAM_WORDS, error=error), ONEPLAY_STORAGE)
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_probe.py
git commit -m "test(red): probe_device" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.application.probe'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/application/probe.py`:

```python
"""Validación de un equipo nuevo: lectura de la entidad de prueba del perfil."""

from ..domain.decode import decode
from ..domain.profile import DeviceProfile
from ..ports.device import DeviceGateway


async def probe_device(gateway: DeviceGateway, profile: DeviceProfile) -> None:
    spec = next(e for e in profile.entities if e.key == profile.probe_key)
    words = await gateway.read([spec.register])
    # DecodeError si el valor no es válido (por ejemplo, fuera del enum)
    decode(spec, words[spec.register])
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/application/probe.py
git commit -m "feat(application): probe_device" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 9: `ModbusGateway`

**Files:**
- Create: `custom_components/modbus_solar/adapters/outbound/modbus_gateway.py`
- Test: `tests/unit/test_modbus_gateway.py`

**Interfaces:**
- Consumes: `plan_blocks` (Tarea 4), errores (Tarea 2) y `ONEPLAY_STORAGE` (Tarea 6).
- Consumes de `modbus_connection` 4.10.0: `ModbusUnit`, `ModbusConnectionError`,
  `ModbusTimeoutError`, `ModbusProtocolError` y `ModbusExceptionError`.
- En tests: `modbus_connection.mock.MockModbusConnection`. Su `for_unit(1)` devuelve un
  `MockModbusUnit` con `holding`, `input`, `read_events`, `message_spacing`,
  `fail_read(address, error, *, register_type="holding")` y `fail_requests(error)`.
  Los reads se registran en `read_events` antes de lanzar el fallo (`mock.py`, `_dispatch_read`).
- Produces: `ModbusGateway(unit: ModbusUnit, profile: DeviceProfile, max_gap: int = 0)`, que
  implementa `DeviceGateway`.
  - Al crearse llama a `unit.set_message_spacing(profile.min_request_interval_s)`.
  - `read` lanza una petición por bloque (`read_holding_registers` / `read_input_registers`)
    y devuelve `{spec: tuple(palabras)}`.
  - Traduce `ModbusConnectionError` y `ModbusTimeoutError` a `DeviceUnavailable`, y
    `ModbusExceptionError` y `ModbusProtocolError` a `DeviceProtocolError`.

- [ ] **Paso 1: Test que falla**

`tests/unit/test_modbus_gateway.py`:

```python
"""ModbusGateway sobre el mock en memoria de modbus_connection."""

import pytest
from modbus_connection import ModbusConnectionError, ModbusExceptionError, ModbusProtocolError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit, ReadEvent

from custom_components.modbus_solar.adapters.outbound.modbus_gateway import ModbusGateway
from custom_components.modbus_solar.domain.errors import DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.domain.profile import RegisterSpec
from custom_components.modbus_solar.domain.types import DataType, RegisterKind
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE

SPECS = [e.register for e in ONEPLAY_STORAGE.entities]


@pytest.fixture
def unit() -> MockModbusUnit:
    unit = MockModbusConnection().for_unit(1)
    unit.holding.update({0x101D: 3, 0x1021: [0, 50000], 0x1037: [0, 12345]})
    return unit


def test_sets_message_spacing_from_profile(unit: MockModbusUnit) -> None:
    ModbusGateway(unit, ONEPLAY_STORAGE)
    assert unit.message_spacing == 1.0


async def test_one_request_per_block(unit: MockModbusUnit) -> None:
    words = await ModbusGateway(unit, ONEPLAY_STORAGE).read(SPECS)
    assert unit.read_events == [
        ReadEvent("holding", 0x101D, 1),
        ReadEvent("holding", 0x1021, 2),
        ReadEvent("holding", 0x1037, 2),
    ]
    # SPECS va en el orden del perfil: inverter_state, active_power, total_energy
    assert [words[spec] for spec in SPECS] == [(3,), (0, 12345), (0, 50000)]


async def test_contiguous_registers_in_one_request(unit: MockModbusUnit) -> None:
    unit.holding.update({10: 1, 11: [2, 3]})
    specs = [RegisterSpec(address=10, dtype=DataType.U16), RegisterSpec(address=11, dtype=DataType.U32)]
    words = await ModbusGateway(unit, ONEPLAY_STORAGE).read(specs)
    assert unit.read_events == [ReadEvent("holding", 10, 3)]
    assert words == {specs[0]: (1,), specs[1]: (2, 3)}


async def test_max_gap_reads_through_gaps(unit: MockModbusUnit) -> None:
    specs = [RegisterSpec(address=10, dtype=DataType.U16), RegisterSpec(address=13, dtype=DataType.U16)]
    await ModbusGateway(unit, ONEPLAY_STORAGE, max_gap=2).read(specs)
    assert unit.read_events == [ReadEvent("holding", 10, 4)]


async def test_input_registers_use_fc04(unit: MockModbusUnit) -> None:
    unit.input[5] = 42
    spec = RegisterSpec(address=5, dtype=DataType.U16, kind=RegisterKind.INPUT)
    assert await ModbusGateway(unit, ONEPLAY_STORAGE).read([spec]) == {spec: (42,)}
    assert unit.read_events == [ReadEvent("input", 5, 1)]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ModbusConnectionError("refused"), DeviceUnavailable),
        (ModbusTimeoutError("timeout"), DeviceUnavailable),
        (ModbusProtocolError("bad frame"), DeviceProtocolError),
        (ModbusExceptionError(2), DeviceProtocolError),
    ],
)
async def test_translates_modbus_errors(unit: MockModbusUnit, error: Exception, expected: type[Exception]) -> None:
    unit.fail_read(0x1021, error)
    with pytest.raises(expected):
        await ModbusGateway(unit, ONEPLAY_STORAGE).read(SPECS)


async def test_dead_device_is_unavailable(unit: MockModbusUnit) -> None:
    unit.fail_requests(ModbusConnectionError("no route"))
    with pytest.raises(DeviceUnavailable):
        await ModbusGateway(unit, ONEPLAY_STORAGE).read(SPECS)
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_modbus_gateway.py
git commit -m "test(red): ModbusGateway" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.adapters.outbound.modbus_gateway'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py`:

```python
"""DeviceGateway sobre una ModbusUnit compartida (integración modbus del core)."""

from collections.abc import Mapping, Sequence

from modbus_connection import (
    ModbusConnectionError,
    ModbusExceptionError,
    ModbusProtocolError,
    ModbusTimeoutError,
    ModbusUnit,
)

from ...domain.blocks import plan_blocks
from ...domain.errors import DeviceProtocolError, DeviceUnavailable
from ...domain.profile import DeviceProfile, RegisterSpec
from ...domain.types import RegisterKind


class ModbusGateway:
    def __init__(self, unit: ModbusUnit, profile: DeviceProfile, max_gap: int = 0) -> None:
        self._unit = unit
        self._max_gap = max_gap
        self._max_count = profile.max_block_registers
        # la librería espacia las peticiones de esta unit dentro de la conexión compartida
        unit.set_message_spacing(profile.min_request_interval_s)

    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]:
        words: dict[tuple[RegisterKind, int], int] = {}
        for block in plan_blocks(specs, self._max_gap, self._max_count):
            if block.kind is RegisterKind.HOLDING:
                request = self._unit.read_holding_registers
            else:
                request = self._unit.read_input_registers
            try:
                values = await request(block.address, block.count)
            except (ModbusConnectionError, ModbusTimeoutError) as err:
                raise DeviceUnavailable(str(err)) from err
            except (ModbusExceptionError, ModbusProtocolError) as err:
                raise DeviceProtocolError(str(err)) from err
            if len(values) != block.count:
                raise DeviceProtocolError(f"expected {block.count} registers at {block.address}, got {len(values)}")
            for offset, value in enumerate(values):
                words[(block.kind, block.address + offset)] = value
        return {spec: tuple(words[(spec.kind, spec.address + i)] for i in range(spec.dtype.words)) for spec in specs}
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/adapters/outbound/modbus_gateway.py
git commit -m "feat(adapters): ModbusGateway con bloques y traducción de errores" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 10: `TierCoordinator` y `DeviceRuntime`

**Files:**
- Create: `custom_components/modbus_solar/adapters/inbound/coordinator.py`,
  `custom_components/modbus_solar/adapters/inbound/runtime.py`
- Create: `tests/ha/__init__.py` (vacío), `tests/ha/conftest.py`, `tests/ha/common.py`
- Test: `tests/ha/test_coordinator.py`, `tests/unit/test_unique_ids.py`

**Interfaces:**
- Consumes: `read_tier`, `TierResult` (Tarea 7), errores (Tarea 2), `ONEPLAY_STORAGE`
  (Tarea 6), `FakeGateway` e `INGETEAM_WORDS` (Tarea 7), constantes de `const.py` (Tarea 1).
- Produces (`coordinator.py`): `TierCoordinator(DataUpdateCoordinator[TierResult])` con
  `__init__(hass, entry, *, name: str, tier: PollTier, interval_s: int, gateway: DeviceGateway, profile: DeviceProfile, keys: Iterable[str])`.
  - Atributos públicos: `tier`, `keys: frozenset[str]`, `last_error: str | None` y
    `last_error_at: datetime | None`.
  - `always_update=False` y `update_interval=timedelta(seconds=interval_s)`.
  - `DeviceUnavailable` y `DeviceProtocolError` se convierten en `UpdateFailed`;
    `last_error` vale `"<Clase>: <mensaje>"`.
  - Un `DecodeError` registra un `warning` por clave, una sola vez hasta que la clave se recupera.
- Produces (`runtime.py`):
  - `DeviceRuntime` (dataclass) con `subentry_id: str`, `title: str`, `profile: DeviceProfile`,
    `intervals: dict[str, int]`, `gateway: DeviceGateway` y `coordinators: dict[PollTier, TierCoordinator]`.
  - `type ModbusSolarConfigEntry = ConfigEntry[dict[str, DeviceRuntime]]`.
  - `entity_unique_id(subentry_id: str, key: str) -> str`, que devuelve `f"{subentry_id}_{key}"`.
  - `enabled_keys(registry: er.EntityRegistry, subentry_id: str, profile: DeviceProfile) -> frozenset[str]`.
  - `build_runtime(hass, entry, subentry: ConfigSubentry, profile, gateway, keys) -> DeviceRuntime`:
    crea un coordinator por cada tier que tenga entidades en el perfil.
- Produces (`tests/ha/common.py`): `DEVICE_ID = "dev1"`, `DEVICE_DATA`,
  `DEVICE = (DEVICE_ID, "Inverter", DEVICE_DATA)`, `brand_entry(*devices) -> MockConfigEntry`,
  `entity_id_of(hass, key, subentry_id=DEVICE_ID)`, `state_of(hass, key)`,
  `async setup_entry(hass, entry)` y `async tick(hass, seconds)`.
- Produces (`tests/ha/conftest.py`): fixture autouse `auto_enable_custom_integrations` y
  fixture `ingeteam_unit -> MockModbusUnit`, con los registros de `INGETEAM_WORDS` cargados.

- [ ] **Paso 1: Utilidades de test y tests que fallan**

`tests/ha/conftest.py`:

```python
"""Fixtures de los tests con hass."""

import pytest
from modbus_connection.mock import MockModbusConnection, MockModbusUnit


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Permite cargar custom_components/ en cada test."""


@pytest.fixture
def ingeteam_unit() -> MockModbusUnit:
    # mismos valores que tests.fakes.INGETEAM_WORDS: grid_connected, 5000.0 Wh y 1234.5 W
    unit = MockModbusConnection().for_unit(1)
    unit.holding.update({0x101D: 3, 0x1021: [0, 50000], 0x1037: [0, 12345]})
    return unit
```

`tests/ha/common.py`:

```python
"""Datos y utilidades compartidos por los tests con hass."""

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.modbus_solar.const import DOMAIN

DEVICE_ID = "dev1"
DEVICE_DATA: dict[str, Any] = {
    "host": "192.168.1.50",
    "port": 502,
    "unit_id": 1,
    "profile": "ingeteam.oneplay_storage",
    "intervals": {"fast": 5, "normal": 60, "slow": 3600},
}
DEVICE = (DEVICE_ID, "Inverter", DEVICE_DATA)


def brand_entry(*devices: tuple[str, str, dict[str, Any]]) -> MockConfigEntry:
    """Entry de marca Ingeteam con una subentry `device` por tupla (subentry_id, title, data)."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Ingeteam",
        data={"brand": "ingeteam"},
        unique_id="ingeteam",
        subentries_data=[
            {
                "subentry_id": subentry_id,
                "subentry_type": "device",
                "title": title,
                "unique_id": f"{data['host']}:{data['port']}:{data['unit_id']}",
                "data": data,
            }
            for subentry_id, title, data in devices
        ],
    )


def entity_id_of(hass: HomeAssistant, key: str, subentry_id: str = DEVICE_ID) -> str | None:
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{subentry_id}_{key}")


def state_of(hass: HomeAssistant, key: str) -> State | None:
    entity_id = entity_id_of(hass, key)
    return None if entity_id is None else hass.states.get(entity_id)


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    # el primer refresh de cada coordinator va en segundo plano
    await hass.async_block_till_done(wait_background_tasks=True)


async def tick(hass: HomeAssistant, seconds: float) -> None:
    """Avanza el reloj de HA; usar intervalo + 1 para disparar un tier."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done(wait_background_tasks=True)
```

`tests/unit/test_unique_ids.py`:

```python
"""Formatos de unique_id estables: cambiarlos duplica entidades en instalaciones existentes."""

from custom_components.modbus_solar.adapters.inbound.runtime import entity_unique_id


def test_entity_unique_id_format() -> None:
    assert entity_unique_id("01JABCDEF", "active_power") == "01JABCDEF_active_power"
```

`tests/ha/test_coordinator.py`:

```python
"""TierCoordinator, enabled_keys y build_runtime con hass."""

import logging
from dataclasses import replace
from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.modbus_solar.adapters.inbound.coordinator import TierCoordinator
from custom_components.modbus_solar.adapters.inbound.runtime import build_runtime, enabled_keys
from custom_components.modbus_solar.const import DOMAIN
from custom_components.modbus_solar.domain.errors import DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.domain.types import PollTier
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE
from tests.fakes import INGETEAM_WORDS, FakeGateway
from tests.ha.common import DEVICE, DEVICE_ID, brand_entry

ALL_KEYS = frozenset({"inverter_state", "active_power", "total_energy"})


def make_coordinator(hass: HomeAssistant, gateway: FakeGateway) -> TierCoordinator:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    return TierCoordinator(
        hass,
        entry,
        name="Inverter fast",
        tier=PollTier.FAST,
        interval_s=5,
        gateway=gateway,
        profile=ONEPLAY_STORAGE,
        keys=ALL_KEYS,
    )


async def test_refresh_stores_tier_result(hass: HomeAssistant) -> None:
    coordinator = make_coordinator(hass, FakeGateway(INGETEAM_WORDS))
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.data.values == {"inverter_state": "grid_connected", "active_power": 1234.5}
    assert coordinator.update_interval == timedelta(seconds=5)
    assert (coordinator.tier, coordinator.keys) == (PollTier.FAST, ALL_KEYS)
    assert (coordinator.last_error, coordinator.last_error_at) == (None, None)


@pytest.mark.parametrize("error", [DeviceUnavailable("timeout"), DeviceProtocolError("exception 2")])
async def test_domain_errors_fail_the_update(hass: HomeAssistant, error: Exception) -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    coordinator = make_coordinator(hass, gateway)
    await coordinator.async_refresh()
    gateway.error = error
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert coordinator.last_error == f"{type(error).__name__}: {error}"
    assert coordinator.last_error_at is not None
    # data conserva la última lectura correcta (para diagnostics)
    assert coordinator.data.values["active_power"] == 1234.5


async def test_decode_warning_once_per_key_until_recovery(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    gateway = FakeGateway({**INGETEAM_WORDS, 0x101D: (7,)})
    coordinator = make_coordinator(hass, gateway)
    await coordinator.async_refresh()
    await coordinator.async_refresh()
    assert caplog.text.count("value 7 not in enum") == 1
    assert coordinator.last_update_success
    gateway.words[0x101D] = (3,)
    await coordinator.async_refresh()
    gateway.words[0x101D] = (7,)
    await coordinator.async_refresh()
    assert caplog.text.count("value 7 not in enum") == 2


async def test_enabled_keys_follow_entity_registry(hass: HomeAssistant) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    # sin entidades registradas: manda enabled_default del perfil
    assert enabled_keys(registry, DEVICE_ID, ONEPLAY_STORAGE) == ALL_KEYS
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DEVICE_ID}_active_power",
        config_entry=entry,
        config_subentry_id=DEVICE_ID,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    assert enabled_keys(registry, DEVICE_ID, ONEPLAY_STORAGE) == ALL_KEYS - {"active_power"}


async def test_enabled_keys_respect_enabled_default(hass: HomeAssistant) -> None:
    state, *rest = ONEPLAY_STORAGE.entities
    profile = replace(ONEPLAY_STORAGE, entities=(replace(state, enabled_default=False), *rest))
    assert enabled_keys(er.async_get(hass), DEVICE_ID, profile) == ALL_KEYS - {"inverter_state"}


async def test_build_runtime_one_coordinator_per_tier_with_entities(hass: HomeAssistant) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    gateway = FakeGateway(INGETEAM_WORDS)
    runtime = build_runtime(hass, entry, entry.subentries[DEVICE_ID], ONEPLAY_STORAGE, gateway, ALL_KEYS)
    assert (runtime.subentry_id, runtime.title, runtime.profile.id) == (DEVICE_ID, "Inverter", ONEPLAY_STORAGE.id)
    assert runtime.intervals == {"fast": 5, "normal": 60, "slow": 3600}
    assert runtime.gateway is gateway
    # el perfil Ingeteam no tiene entidades slow
    assert set(runtime.coordinators) == {PollTier.FAST, PollTier.NORMAL}
    assert runtime.coordinators[PollTier.NORMAL].update_interval == timedelta(seconds=60)
    assert runtime.coordinators[PollTier.FAST].keys == ALL_KEYS
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/ha tests/unit/test_unique_ids.py
git commit -m "test(red): TierCoordinator y DeviceRuntime" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.adapters.inbound.runtime'`
(y `...inbound.coordinator`).

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/adapters/inbound/coordinator.py`:

```python
"""Un DataUpdateCoordinator por tier de sondeo de un equipo."""

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from ...application.poller import TierResult, read_tier
from ...domain.errors import DeviceProtocolError, DeviceUnavailable
from ...domain.profile import DeviceProfile
from ...domain.types import PollTier
from ...ports.device import DeviceGateway

_LOGGER = logging.getLogger(__name__)


class TierCoordinator(DataUpdateCoordinator[TierResult]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        name: str,
        tier: PollTier,
        interval_s: int,
        gateway: DeviceGateway,
        profile: DeviceProfile,
        keys: Iterable[str],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=name,
            update_interval=timedelta(seconds=interval_s),
            # HA solo escribe estado si el TierResult cambia
            always_update=False,
        )
        self.tier = tier
        self.keys = frozenset(keys)
        self.last_error: str | None = None
        self.last_error_at: datetime | None = None
        self._gateway = gateway
        self._profile = profile
        self._warned: set[str] = set()

    async def _async_update_data(self) -> TierResult:
        try:
            result = await read_tier(self.tier, self._gateway, self._profile, self.keys)
        except (DeviceUnavailable, DeviceProtocolError) as err:
            self.last_error = f"{type(err).__name__}: {err}"
            self.last_error_at = dt_util.utcnow()
            # DataUpdateCoordinator registra un error al perder el equipo y un info al recuperarlo
            raise UpdateFailed(str(err)) from err
        for key, message in result.decode_errors.items():
            if key not in self._warned:
                _LOGGER.warning("%s: %s", self.name, message)
        # una clave que vuelve a decodificar bien puede volver a avisar
        self._warned = set(result.decode_errors)
        return result
```

`custom_components/modbus_solar/adapters/inbound/runtime.py`:

```python
"""Estado en memoria de cada equipo (subentry) mientras la entry de marca está cargada."""

from collections.abc import Collection
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ...const import CONF_INTERVALS, DEFAULT_INTERVALS, DOMAIN
from ...domain.profile import DeviceProfile
from ...domain.types import PollTier
from ...ports.device import DeviceGateway
from .coordinator import TierCoordinator


@dataclass
class DeviceRuntime:
    subentry_id: str
    title: str
    profile: DeviceProfile
    intervals: dict[str, int]
    gateway: DeviceGateway
    coordinators: dict[PollTier, TierCoordinator]


type ModbusSolarConfigEntry = ConfigEntry[dict[str, DeviceRuntime]]


def entity_unique_id(subentry_id: str, key: str) -> str:
    # basado en el subentry_id (ULID): cambiar el host no duplica entidades
    return f"{subentry_id}_{key}"


def enabled_keys(registry: er.EntityRegistry, subentry_id: str, profile: DeviceProfile) -> frozenset[str]:
    keys: set[str] = set()
    for spec in profile.entities:
        entity_id = registry.async_get_entity_id(spec.platform, DOMAIN, entity_unique_id(subentry_id, spec.key))
        if entity_id is None:
            # entidad aún no registrada: manda el valor por defecto del perfil
            if spec.enabled_default:
                keys.add(spec.key)
        elif (entity := registry.async_get(entity_id)) is not None and entity.disabled_by is None:
            keys.add(spec.key)
    return frozenset(keys)


def build_runtime(
    hass: HomeAssistant,
    entry: ConfigEntry,
    subentry: ConfigSubentry,
    profile: DeviceProfile,
    gateway: DeviceGateway,
    keys: Collection[str],
) -> DeviceRuntime:
    intervals = {**DEFAULT_INTERVALS, **subentry.data.get(CONF_INTERVALS, {})}
    coordinators = {
        tier: TierCoordinator(
            hass,
            entry,
            name=f"{subentry.title} {tier}",
            tier=tier,
            interval_s=intervals[tier],
            gateway=gateway,
            profile=profile,
            keys=keys,
        )
        for tier in PollTier
        if any(e.poll is tier for e in profile.entities)
    }
    return DeviceRuntime(
        subentry_id=subentry.subentry_id,
        title=subentry.title,
        profile=profile,
        intervals=intervals,
        gateway=gateway,
        coordinators=coordinators,
    )
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/adapters/inbound
git commit -m "feat(inbound): TierCoordinator y DeviceRuntime" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 11: Traducciones

Van antes que los flows y las entidades: los tests de flow y de entidades ya encuentran los textos.

**Files:**
- Create: `custom_components/modbus_solar/strings.json`,
  `custom_components/modbus_solar/translations/en.json`,
  `custom_components/modbus_solar/translations/es.json`
- Test: `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: `ALL_PROFILES` (Tarea 6).
- Produces: claves de texto que usan las Tareas 12-14.
  - `config.step.user` (campo `brand`) y `config.abort.already_configured`.
  - `config_subentries.device`, con:
    - `entry_type` e `initiate_flow.user`;
    - pasos `user` (`name`, `host`, `port`, `unit_id`, `profile`) y `reconfigure`
      (`host`, `port`, `fast`, `normal`, `slow`);
    - errores `cannot_connect`, `endpoint_in_use`, `invalid_response` e `interval_too_short`;
    - aborts `already_configured` y `reconfigure_successful`.
  - `entity.sensor.<key>.name` para cada clave y `state` para los estados del enum.
- Regla: `translations/en.json` es copia literal de `strings.json`. Una custom integration no
  resuelve referencias `[%key:…%]`, así que no se usan.

- [ ] **Paso 1: Test que falla**

`tests/unit/test_translations.py`:

```python
"""Traducciones: en.json igual a strings.json; es.json con las mismas claves; nada sin traducir."""

import json
from pathlib import Path
from typing import Any

from custom_components.modbus_solar.profiles import ALL_PROFILES

ROOT = Path(__file__).parents[2] / "custom_components" / "modbus_solar"


def load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def leaf_paths(tree: dict[str, Any], prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for key, value in tree.items():
        path = f"{prefix}{key}"
        paths |= leaf_paths(value, f"{path}.") if isinstance(value, dict) else {path}
    return paths


def test_en_is_literal_copy_of_strings() -> None:
    assert load("translations/en.json") == load("strings.json")


def test_es_has_the_same_keys() -> None:
    assert leaf_paths(load("translations/es.json")) == leaf_paths(load("strings.json"))


def test_every_entity_and_enum_state_is_translated() -> None:
    sensors = load("strings.json")["entity"]["sensor"]
    for profile in ALL_PROFILES:
        for spec in profile.entities:
            assert "name" in sensors[spec.key], spec.key
            if spec.enum is not None:
                assert set(sensors[spec.key]["state"]) == set(spec.enum.values()), spec.key


def test_flow_errors_and_aborts_are_translated() -> None:
    strings = load("strings.json")
    device = strings["config_subentries"]["device"]
    assert set(device["error"]) == {"cannot_connect", "endpoint_in_use", "invalid_response", "interval_too_short"}
    assert set(device["abort"]) == {"already_configured", "reconfigure_successful"}
    assert set(device["step"]) == {"user", "reconfigure"}
    assert set(strings["config"]["abort"]) == {"already_configured"}
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_translations.py
git commit -m "test(red): traducciones" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `FileNotFoundError` de `translations/en.json`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/strings.json` y `custom_components/modbus_solar/translations/en.json`
(mismo contenido, byte a byte):

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Choose a brand",
        "description": "One entry per brand. Add each device afterwards from the entry.",
        "data": {
          "brand": "Brand"
        }
      }
    },
    "abort": {
      "already_configured": "This brand is already configured."
    }
  },
  "config_subentries": {
    "device": {
      "entry_type": "Device",
      "initiate_flow": {
        "user": "Add device"
      },
      "step": {
        "user": {
          "title": "Add device",
          "data": {
            "name": "Name",
            "host": "Host",
            "port": "Port",
            "unit_id": "Unit ID",
            "profile": "Model"
          }
        },
        "reconfigure": {
          "title": "Reconfigure device",
          "data": {
            "host": "Host",
            "port": "Port",
            "fast": "Fast poll interval (s)",
            "normal": "Normal poll interval (s)",
            "slow": "Slow poll interval (s)"
          }
        }
      },
      "error": {
        "cannot_connect": "The device does not answer. Check host, port and unit ID, and that no other Modbus client is using the device.",
        "endpoint_in_use": "This endpoint is already in use with different connection settings.",
        "invalid_response": "The device answered with an unexpected value. Check the model and the unit ID.",
        "interval_too_short": "Too short for this device: reading all its registers takes longer."
      },
      "abort": {
        "already_configured": "This device is already configured.",
        "reconfigure_successful": "The device was reconfigured."
      }
    }
  },
  "entity": {
    "sensor": {
      "inverter_state": {
        "name": "Inverter state",
        "state": {
          "factory_default": "Factory default",
          "grid_disconnected": "Disconnected from grid",
          "grid_connected": "Connected to grid"
        }
      },
      "active_power": {
        "name": "Active power"
      },
      "total_energy": {
        "name": "Total energy"
      }
    }
  }
}
```

`custom_components/modbus_solar/translations/es.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Elige una marca",
        "description": "Una entrada por marca. Después añade cada equipo desde la entrada.",
        "data": {
          "brand": "Marca"
        }
      }
    },
    "abort": {
      "already_configured": "Esta marca ya está configurada."
    }
  },
  "config_subentries": {
    "device": {
      "entry_type": "Equipo",
      "initiate_flow": {
        "user": "Añadir equipo"
      },
      "step": {
        "user": {
          "title": "Añadir equipo",
          "data": {
            "name": "Nombre",
            "host": "Host",
            "port": "Puerto",
            "unit_id": "ID de unidad",
            "profile": "Modelo"
          }
        },
        "reconfigure": {
          "title": "Reconfigurar equipo",
          "data": {
            "host": "Host",
            "port": "Puerto",
            "fast": "Intervalo de sondeo rápido (s)",
            "normal": "Intervalo de sondeo normal (s)",
            "slow": "Intervalo de sondeo lento (s)"
          }
        }
      },
      "error": {
        "cannot_connect": "El equipo no responde. Revisa host, puerto e ID de unidad, y que ningún otro cliente Modbus esté usando el equipo.",
        "endpoint_in_use": "Este endpoint ya está en uso con otros parámetros de conexión.",
        "invalid_response": "El equipo respondió con un valor inesperado. Revisa el modelo y el ID de unidad.",
        "interval_too_short": "Demasiado corto para este equipo: leer todos sus registros tarda más."
      },
      "abort": {
        "already_configured": "Este equipo ya está configurado.",
        "reconfigure_successful": "El equipo se ha reconfigurado."
      }
    }
  },
  "entity": {
    "sensor": {
      "inverter_state": {
        "name": "Estado del inversor",
        "state": {
          "factory_default": "Configuración de fábrica",
          "grid_disconnected": "Desconectado de la red",
          "grid_connected": "Conectado a la red"
        }
      },
      "active_power": {
        "name": "Potencia activa"
      },
      "total_energy": {
        "name": "Energía total"
      }
    }
  }
}
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/strings.json custom_components/modbus_solar/translations
git commit -m "feat: traducciones en y es" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 12: Config flow de marca y subentry flow de equipo

**Files:**
- Create: `custom_components/modbus_solar/adapters/inbound/flow.py`,
  `custom_components/modbus_solar/config_flow.py`
- Modify: `tests/ha/conftest.py` (fixture `temp_unit`), `tests/unit/test_unique_ids.py`
- Test: `tests/ha/test_config_flow.py`, `tests/ha/test_subentry_flow.py`

**Interfaces:**
- Consumes: `Catalog` y `CATALOG` (Tarea 6), `probe_device` (Tarea 8), `ModbusGateway`
  (Tarea 9) y errores (Tarea 2).
- Consumes de HA 2026.9: `async_get_temporary_unit(hass, params, unit_id)` de
  `homeassistant.components.modbus`. Es un asynccontextmanager que lanza `HomeAssistantError`
  si el endpoint ya está en uso con otros parámetros.
- Produces (`flow.py`):
  - `GatewayFactory`: `Callable[[HomeAssistant, str, int, int, DeviceProfile], AbstractAsyncContextManager[DeviceGateway]]`.
    Recibe `(hass, host, port, unit_id, profile)`. Si el endpoint está en uso, lanza `EndpointInUse`
    (dominio). El flow nunca ve `HomeAssistantError`.
  - Validadores `PORT` (1-65535), `UNIT_ID` (1-247) e `INTERVAL` (≥ 1).
  - `device_unique_id(host: str, port: int, unit_id: int) -> str`, que devuelve `f"{host.lower()}:{port}:{unit_id}"`.
  - `BrandFlow(ConfigFlow)` sin `domain`, `VERSION = 1`. Atributos de clase:
    `catalog: Catalog` y `device_flow: type[ConfigSubentryFlow]`.
  - `DeviceSubentryFlow(ConfigSubentryFlow)`. Atributos de clase: `catalog: Catalog` y
    `gateway_factory: GatewayFactory` (con `staticmethod`).
  - `DeviceSubentryFlow._unique_id_taken(entry, unique_id, exclude=None) -> bool`.
    La reutiliza la Tarea 13.
- Produces (`config_flow.py`): `open_gateway` (`GatewayFactory` real),
  `DeviceFlow(DeviceSubentryFlow)` y `ModbusSolarConfigFlow(BrandFlow, domain=DOMAIN)`.
- Produces (`tests/ha/conftest.py`): fixture `temp_unit -> MagicMock`, que parchea
  `custom_components.modbus_solar.config_flow.async_get_temporary_unit` y entrega `ingeteam_unit`.

- [ ] **Paso 1: Tests que fallan**

Añadir al final de `tests/ha/conftest.py`, con estos imports arriba:

```python
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import MagicMock, patch
```

```python
@pytest.fixture
def temp_unit(ingeteam_unit: MockModbusUnit) -> Generator[MagicMock]:
    """Sustituye la unit temporal del config flow por ingeteam_unit."""

    @asynccontextmanager
    async def fake(hass: Any, params: Any, unit_id: int) -> AsyncIterator[MockModbusUnit]:
        yield ingeteam_unit

    with patch("custom_components.modbus_solar.config_flow.async_get_temporary_unit", side_effect=fake) as mock:
        yield mock
```

Añadir a `tests/unit/test_unique_ids.py`:

```python
from custom_components.modbus_solar.adapters.inbound.flow import device_unique_id


def test_device_unique_id_format() -> None:
    assert device_unique_id("Inverter.LAN", 502, 1) == "inverter.lan:502:1"
```

`tests/ha/test_config_flow.py`:

```python
"""Config flow de la entry de marca."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

# registra el handler en HANDLERS: supported_subentry_types lo busca ahí sin importar nada
import custom_components.modbus_solar.config_flow  # noqa: F401
from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import brand_entry


async def test_brand_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"brand": "ingeteam"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (result["title"], result["data"]) == ("Ingeteam", {"brand": "ingeteam"})
    assert result["result"].unique_id == "ingeteam"


async def test_brand_flow_aborts_if_brand_exists(hass: HomeAssistant) -> None:
    brand_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"brand": "ingeteam"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_brand_entry_offers_device_subentries(hass: HomeAssistant) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    assert set(entry.supported_subentry_types) == {"device"}
```

`tests/ha/test_subentry_flow.py`:

```python
"""Subentry flow `device`: alta de un equipo con sonda Modbus."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusConnectionError, ModbusExceptionError, ModbusTcpParams
from modbus_connection.mock import MockModbusUnit

from tests.ha.common import DEVICE, brand_entry

USER_INPUT = {
    "name": "Inverter",
    "host": "192.168.1.50",
    "port": 502,
    "unit_id": 1,
    "profile": "ingeteam.oneplay_storage",
}


async def submit(hass: HomeAssistant, entry_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
    result = await hass.config_entries.subentries.async_init((entry_id, "device"), context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)


async def test_add_device(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    result = await submit(hass, entry.entry_id, {**USER_INPUT, "host": "Inverter.LAN"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    subentry = next(iter(entry.subentries.values()))
    assert (subentry.subentry_type, subentry.title, subentry.unique_id) == ("device", "Inverter", "inverter.lan:502:1")
    assert dict(subentry.data) == {
        "host": "Inverter.LAN",
        "port": 502,
        "unit_id": 1,
        "profile": "ingeteam.oneplay_storage",
        "intervals": {"fast": 5, "normal": 60, "slow": 3600},
    }
    _, params, unit_id = temp_unit.call_args.args
    assert (params, unit_id) == (ModbusTcpParams(host="Inverter.LAN", port=502), 1)


async def test_duplicate_device_aborts_before_probing(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    result = await submit(hass, entry.entry_id, USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    temp_unit.assert_not_called()


@pytest.mark.parametrize(
    ("break_device", "error"),
    [
        (lambda unit, mock: unit.fail_requests(ModbusConnectionError("refused")), "cannot_connect"),
        (lambda unit, mock: unit.fail_read(0x101D, ModbusExceptionError(2)), "invalid_response"),
        (lambda unit, mock: unit.holding.update({0x101D: 7}), "invalid_response"),
        (lambda unit, mock: setattr(mock, "side_effect", HomeAssistantError("in use")), "endpoint_in_use"),
    ],
)
async def test_probe_errors_show_form_error(
    hass: HomeAssistant,
    temp_unit: MagicMock,
    ingeteam_unit: MockModbusUnit,
    break_device: Any,
    error: str,
) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    break_device(ingeteam_unit, temp_unit)
    result = await submit(hass, entry.entry_id, USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert entry.subentries == {}


async def test_form_recovers_after_error(
    hass: HomeAssistant, temp_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    ingeteam_unit.fail_requests(ModbusConnectionError("refused"))
    result = await submit(hass, entry.entry_id, USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}
    ingeteam_unit.fail_requests(None)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/ha tests/unit/test_unique_ids.py
git commit -m "test(red): config flow de marca y subentry flow de equipo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo. `test_unique_ids.py` falla con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.adapters.inbound.flow'`;
los tests de flow fallan con `UnknownHandler` o porque no se puede parchear `config_flow.async_get_temporary_unit`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/adapters/inbound/flow.py`:

```python
"""Config flow de marca y subentry flow de equipo. Catálogo y gateway los inyecta config_flow.py."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, ClassVar

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback

from ...application.catalog import Catalog
from ...application.probe import probe_device
from ...const import (
    BRAND_TITLES,
    CONF_BRAND,
    CONF_INTERVALS,
    CONF_PROFILE,
    CONF_UNIT_ID,
    DEFAULT_INTERVALS,
    SUBENTRY_DEVICE,
)
from ...domain.errors import DecodeError, DeviceProtocolError, DeviceUnavailable, EndpointInUse
from ...domain.profile import DeviceProfile
from ...ports.device import DeviceGateway

# (hass, host, port, unit_id, profile) -> contexto que entrega un gateway sobre una unit temporal
type GatewayFactory = Callable[
    [HomeAssistant, str, int, int, DeviceProfile], AbstractAsyncContextManager[DeviceGateway]
]

PORT = vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))
UNIT_ID = vol.All(vol.Coerce(int), vol.Range(min=1, max=247))
INTERVAL = vol.All(vol.Coerce(int), vol.Range(min=1))


def device_unique_id(host: str, port: int, unit_id: int) -> str:
    return f"{host.lower()}:{port}:{unit_id}"


class BrandFlow(ConfigFlow):
    """Una entry por marca, sin datos de conexión: los equipos son subentries."""

    VERSION = 1
    catalog: ClassVar[Catalog]
    device_flow: ClassVar[type[ConfigSubentryFlow]]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            brand = user_input[CONF_BRAND]
            await self.async_set_unique_id(brand)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=BRAND_TITLES[brand], data={CONF_BRAND: brand})
        brands = {brand: BRAND_TITLES[brand] for brand in self.catalog.brands()}
        schema = vol.Schema({vol.Required(CONF_BRAND): vol.In(brands)})
        return self.async_show_form(step_id="user", data_schema=schema)

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_DEVICE: cls.device_flow}


class DeviceSubentryFlow(ConfigSubentryFlow):
    """Alta de un equipo: valida la conexión leyendo la entidad probe_key del perfil."""

    catalog: ClassVar[Catalog]
    gateway_factory: ClassVar[GatewayFactory]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        profiles = self.catalog.for_brand(entry.data[CONF_BRAND])
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port, unit_id = user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_UNIT_ID]
            profile = self.catalog.get(user_input[CONF_PROFILE])
            unique_id = device_unique_id(host, port, unit_id)
            # el duplicado se detecta antes de abrir conexión
            if self._unique_id_taken(entry, unique_id):
                return self.async_abort(reason="already_configured")
            error = await self._probe(host, port, unit_id, profile)
            if error is None:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    unique_id=unique_id,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                        CONF_PROFILE: profile.id,
                        CONF_INTERVALS: dict(DEFAULT_INTERVALS),
                    },
                )
            errors["base"] = error
        default = profiles[0]
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=default.default_port): PORT,
                vol.Required(CONF_UNIT_ID, default=default.default_unit_id): UNIT_ID,
                vol.Required(CONF_PROFILE, default=default.id): vol.In({p.id: ", ".join(p.models) for p in profiles}),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    @staticmethod
    def _unique_id_taken(entry: ConfigEntry, unique_id: str, exclude: str | None = None) -> bool:
        return any(s.unique_id == unique_id and s.subentry_id != exclude for s in entry.subentries.values())

    async def _probe(self, host: str, port: int, unit_id: int, profile: DeviceProfile) -> str | None:
        """Clave del error del formulario, o None si el equipo responde bien."""
        try:
            async with self.gateway_factory(self.hass, host, port, unit_id, profile) as gateway:
                await probe_device(gateway, profile)
        except EndpointInUse:
            return "endpoint_in_use"
        except DeviceUnavailable:
            return "cannot_connect"
        except (DeviceProtocolError, DecodeError):
            return "invalid_response"
        return None
```

`custom_components/modbus_solar/config_flow.py`:

```python
"""Config flow: compone los flows de adapters/inbound con el catálogo y el gateway Modbus."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusTcpParams

from . import CATALOG
from .adapters.inbound.flow import BrandFlow, DeviceSubentryFlow
from .adapters.outbound.modbus_gateway import ModbusGateway
from .const import DOMAIN
from .domain.errors import EndpointInUse
from .domain.profile import DeviceProfile
from .ports.device import DeviceGateway


@asynccontextmanager
async def open_gateway(
    hass: HomeAssistant, host: str, port: int, unit_id: int, profile: DeviceProfile
) -> AsyncIterator[DeviceGateway]:
    # unit temporal: se cierra al salir si ninguna entry comparte la conexión
    async with AsyncExitStack() as stack:
        try:
            unit = await stack.enter_async_context(
                async_get_temporary_unit(hass, ModbusTcpParams(host=host, port=port), unit_id)
            )
        except HomeAssistantError as err:
            # solo la apertura: endpoint en uso con otros parámetros de enlace
            raise EndpointInUse(str(err)) from err
        yield ModbusGateway(unit, profile)


class DeviceFlow(DeviceSubentryFlow):
    catalog = CATALOG
    gateway_factory = staticmethod(open_gateway)


class ModbusSolarConfigFlow(BrandFlow, domain=DOMAIN):
    catalog = CATALOG
    device_flow = DeviceFlow
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/adapters/inbound/flow.py custom_components/modbus_solar/config_flow.py
git commit -m "feat(inbound): config flow de marca y subentry flow de equipo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`. Al crear la entry de marca, HA intenta montarla y aún no existe
`async_setup_entry` (llega en la Tarea 14). El log mostrará ese error, pero el test solo
comprueba el resultado del flow.

---

### Tarea 13: Reconfigure del equipo

**Files:**
- Modify: `custom_components/modbus_solar/adapters/inbound/flow.py`
- Modify: `tests/ha/test_config_flow.py`
- Test: `tests/ha/test_subentry_flow.py` (añadir tests)

**Interfaces:**
- Consumes: `min_tier_interval` (Tarea 7), `DeviceSubentryFlow._unique_id_taken`,
  `device_unique_id`, `PORT` e `INTERVAL` (Tarea 12).
- Produces: `DeviceSubentryFlow.async_step_reconfigure`.
  - Campos: `host`, `port`, `fast`, `normal` y `slow`.
  - Error por campo `interval_too_short` si un intervalo es menor que `min_tier_interval(profile, tier)`.
  - Abort `already_configured` si el nuevo `unique_id` choca con otra subentry.
  - Si todo va bien, `async_update_and_abort(entry, subentry, unique_id=..., data_updates={host, port, intervals})`,
    que termina en abort `reconfigure_successful`. No cambia `unit_id`, `profile` ni el título.

- [ ] **Paso 1: Tests que fallan**

En `tests/ha/test_config_flow.py`, sustituir el último test por:

```python
async def test_brand_entry_offers_device_subentries(hass: HomeAssistant) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    assert entry.supported_subentry_types == {"device": {"supports_reconfigure": True}}
```

Añadir a `tests/ha/test_subentry_flow.py` (y `SOURCE_RECONFIGURE` al import de
`homeassistant.config_entries`; `DEVICE_DATA` y `DEVICE_ID` al de `tests.ha.common`):

```python
async def reconfigure(
    hass: HomeAssistant, entry_id: str, subentry_id: str, user_input: dict[str, Any]
) -> dict[str, Any]:
    result = await hass.config_entries.subentries.async_init(
        (entry_id, "device"), context={"source": SOURCE_RECONFIGURE, "subentry_id": subentry_id}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    return await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)


RECONFIGURE_INPUT = {"host": "192.168.1.60", "port": 1502, "fast": 10, "normal": 120, "slow": 3600}


async def test_reconfigure_updates_host_port_and_intervals(hass: HomeAssistant) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    result = await reconfigure(hass, entry.entry_id, DEVICE_ID, RECONFIGURE_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    subentry = entry.subentries[DEVICE_ID]
    assert (subentry.title, subentry.unique_id) == ("Inverter", "192.168.1.60:1502:1")
    assert dict(subentry.data) == {
        **DEVICE_DATA,
        "host": "192.168.1.60",
        "port": 1502,
        "intervals": {"fast": 10, "normal": 120, "slow": 3600},
    }


async def test_reconfigure_rejects_interval_shorter_than_blocks(hass: HomeAssistant) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    # fast necesita 2 bloques x 1 s; normal 1 bloque x 1 s; slow no tiene entidades
    result = await reconfigure(hass, entry.entry_id, DEVICE_ID, {**RECONFIGURE_INPUT, "fast": 1, "normal": 1, "slow": 1})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"fast": "interval_too_short"}
    assert entry.subentries[DEVICE_ID].data == DEVICE_DATA


async def test_reconfigure_aborts_if_endpoint_belongs_to_other_device(hass: HomeAssistant) -> None:
    entry = brand_entry(DEVICE, ("dev2", "Inverter 2", {**DEVICE_DATA, "host": "192.168.1.51"}))
    entry.add_to_hass(hass)
    result = await reconfigure(hass, entry.entry_id, "dev2", {**RECONFIGURE_INPUT, "host": "192.168.1.50", "port": 502})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_keeps_own_endpoint(hass: HomeAssistant) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    result = await reconfigure(hass, entry.entry_id, DEVICE_ID, {**RECONFIGURE_INPUT, "host": "192.168.1.50", "port": 502})
    assert result["reason"] == "reconfigure_successful"
    assert entry.subentries[DEVICE_ID].unique_id == "192.168.1.50:502:1"
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/ha
git commit -m "test(red): reconfigure del equipo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo. `supports_reconfigure` vale `False` y el flow aborta con `not_implemented`
porque no hay paso `reconfigure`.

- [ ] **Paso 3: Implementación**

En `custom_components/modbus_solar/adapters/inbound/flow.py`, añadir los imports:

```python
from ...application.poller import min_tier_interval
from ...domain.types import PollTier
```

y este método a `DeviceSubentryFlow`, después de `async_step_user`:

```python
    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        profile = self.catalog.get(subentry.data[CONF_PROFILE])
        errors: dict[str, str] = {}
        if user_input is not None:
            # cada tier tiene que caber en su intervalo con el espaciado entre peticiones
            for tier in PollTier:
                if user_input[tier.value] < min_tier_interval(profile, tier):
                    errors[tier.value] = "interval_too_short"
            if not errors:
                host, port = user_input[CONF_HOST], user_input[CONF_PORT]
                unique_id = device_unique_id(host, port, subentry.data[CONF_UNIT_ID])
                if self._unique_id_taken(entry, unique_id, exclude=subentry.subentry_id):
                    return self.async_abort(reason="already_configured")
                return self.async_update_and_abort(
                    entry,
                    subentry,
                    unique_id=unique_id,
                    data_updates={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_INTERVALS: {tier.value: user_input[tier.value] for tier in PollTier},
                    },
                )
        current = {
            CONF_HOST: subentry.data[CONF_HOST],
            CONF_PORT: subentry.data[CONF_PORT],
            **DEFAULT_INTERVALS,
            **subentry.data.get(CONF_INTERVALS, {}),
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT): PORT,
                **{vol.Required(tier.value): INTERVAL for tier in PollTier},
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or current),
            errors=errors,
        )
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/adapters/inbound/flow.py
git commit -m "feat(inbound): reconfigure de host, puerto e intervalos" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 14: Entidades, setup y unload

**Files:**
- Create: `custom_components/modbus_solar/adapters/inbound/entities/__init__.py`,
  `custom_components/modbus_solar/adapters/inbound/entities/base.py`,
  `custom_components/modbus_solar/adapters/inbound/entities/factory.py`,
  `custom_components/modbus_solar/sensor.py`
- Modify: `custom_components/modbus_solar/__init__.py`, `tests/ha/conftest.py` (fixture `patch_unit`)
- Test: `tests/ha/test_init.py`, `tests/ha/test_sensor.py`

**Interfaces:**
- Consumes: `TierCoordinator`, `DeviceRuntime`, `ModbusSolarConfigEntry`, `entity_unique_id`,
  `enabled_keys` y `build_runtime` (Tarea 10); `ModbusGateway` (Tarea 9); `CATALOG` (Tarea 6).
- Consumes de HA 2026.9: `async_get_unit(hass, entry, params, unit_id)` de
  `homeassistant.components.modbus`. Es `@callback` (síncrona) y libera la unit al descargar la entry.
- Produces:
  - `ModbusSolarEntity(CoordinatorEntity[TierCoordinator])` y `ModbusSolarSensor(ModbusSolarEntity, SensorEntity)`.
  - `build_sensors(runtime: DeviceRuntime, brand_entry_id: str) -> list[ModbusSolarSensor]`.
  - `async_setup_entry` y `async_unload_entry` en el `__init__.py` raíz, y `PLATFORMS`.
- Produces (`tests/ha/conftest.py`): fixture `patch_unit -> MagicMock`, que parchea
  `custom_components.modbus_solar.async_get_unit` y devuelve `ingeteam_unit`.

- [ ] **Paso 1: Tests que fallan**

Añadir al final de `tests/ha/conftest.py`:

```python
@pytest.fixture
def patch_unit(ingeteam_unit: MockModbusUnit) -> Generator[MagicMock]:
    """Sustituye la unit compartida del setup por ingeteam_unit."""
    with patch("custom_components.modbus_solar.async_get_unit", return_value=ingeteam_unit) as mock:
        yield mock
```

`tests/ha/test_init.py`:

```python
"""Setup, unload y recarga de la entry de marca."""

from types import MappingProxyType
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from modbus_connection import ModbusTcpParams
from modbus_connection.mock import MockModbusUnit

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE, DEVICE_DATA, DEVICE_ID, brand_entry, setup_entry


async def test_setup_builds_runtime_and_devices(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert set(entry.runtime_data) == {DEVICE_ID}
    _, called_entry, params, unit_id = patch_unit.call_args.args
    assert (called_entry, params, unit_id) == (entry, ModbusTcpParams(host="192.168.1.50", port=502), 1)
    assert ingeteam_unit.message_spacing == 1.0

    devices = dr.async_get(hass)
    brand = devices.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    device = devices.async_get_device(identifiers={(DOMAIN, DEVICE_ID)})
    assert brand is not None
    assert (brand.name, brand.manufacturer, brand.entry_type) == ("Ingeteam", "Ingeteam", dr.DeviceEntryType.SERVICE)
    assert device is not None
    assert (device.name, device.manufacturer, device.model) == ("Inverter", "Ingeteam", "1Play Storage")
    assert device.via_device_id == brand.id


async def test_unload(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_entry_without_devices_loads(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry()
    await setup_entry(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data == {}
    patch_unit.assert_not_called()


async def test_adding_subentry_reloads_entry(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    second = ConfigSubentry(
        data=MappingProxyType({**DEVICE_DATA, "host": "192.168.1.51"}),
        subentry_type="device",
        title="Inverter 2",
        unique_id="192.168.1.51:502:1",
    )
    hass.config_entries.async_add_subentry(entry, second)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED
    assert set(entry.runtime_data) == {DEVICE_ID, second.subentry_id}


async def test_removing_subentry_reloads_entry(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    hass.config_entries.async_remove_subentry(entry, DEVICE_ID)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data == {}
    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, DEVICE_ID)}) is None
```

`tests/ha/test_sensor.py`:

```python
"""Entidades sensor: valores, disponibilidad y entidades deshabilitadas."""

from unittest.mock import MagicMock

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE, DEVICE_ID, brand_entry, setup_entry, state_of, tick


async def test_values_from_device(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    await setup_entry(hass, brand_entry(DEVICE))
    state = state_of(hass, "inverter_state")
    assert state is not None
    assert state.state == "grid_connected"
    assert state.attributes["options"] == ["factory_default", "grid_disconnected", "grid_connected"]
    power = state_of(hass, "active_power")
    assert power is not None
    assert float(power.state) == 1234.5
    assert power.attributes["unit_of_measurement"] == "W"
    energy = state_of(hass, "total_energy")
    assert energy is not None
    assert float(energy.state) == 5000.0
    assert energy.attributes["state_class"] == "total_increasing"


async def test_entity_registry_unique_ids_and_device(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert {e.unique_id for e in entities} == {
        f"{DEVICE_ID}_inverter_state",
        f"{DEVICE_ID}_active_power",
        f"{DEVICE_ID}_total_energy",
    }
    assert {e.config_subentry_id for e in entities} == {DEVICE_ID}
    assert {e.translation_key for e in entities} == {"inverter_state", "active_power", "total_energy"}


async def test_unavailable_and_recovery(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    await setup_entry(hass, brand_entry(DEVICE))
    ingeteam_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    assert state_of(hass, "active_power").state == STATE_UNAVAILABLE
    assert state_of(hass, "inverter_state").state == STATE_UNAVAILABLE
    # el tier normal (60 s) aún no ha vuelto a leer
    assert float(state_of(hass, "total_energy").state) == 5000.0
    ingeteam_unit.fail_requests(None)
    ingeteam_unit.holding[0x1037] = [0, 20000]
    await tick(hass, 6)
    assert float(state_of(hass, "active_power").state) == 2000.0


async def test_device_down_at_startup_does_not_block_entry(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    ingeteam_unit.fail_requests(ModbusConnectionError("no route"))
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    assert state_of(hass, "active_power").state == STATE_UNAVAILABLE
    assert state_of(hass, "total_energy").state == STATE_UNAVAILABLE


async def test_disabled_entity_is_not_polled(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DEVICE_ID}_active_power",
        config_entry=entry,
        config_subentry_id=DEVICE_ID,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert {event.address for event in ingeteam_unit.read_events} == {0x101D, 0x1021}
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/ha
git commit -m "test(red): setup, entidades y recarga" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `AttributeError: <module 'custom_components.modbus_solar' …> does not have the attribute 'async_get_unit'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/adapters/inbound/entities/__init__.py`:

```python
"""Entidades de Home Assistant construidas desde el perfil."""
```

`custom_components/modbus_solar/adapters/inbound/entities/base.py`:

```python
"""Entidad base: dispositivo, unique_id y disponibilidad según el coordinator de su tier."""

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ....const import BRAND_TITLES, DOMAIN
from ....domain.profile import EntitySpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime, entity_unique_id


class ModbusSolarEntity(CoordinatorEntity[TierCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: EntitySpec, brand_entry_id: str
    ) -> None:
        super().__init__(coordinator)
        self._spec = spec
        self._attr_translation_key = spec.key
        self._attr_unique_id = entity_unique_id(runtime.subentry_id, spec.key)
        self._attr_entity_registry_enabled_default = spec.enabled_default
        if spec.entity_category is not None:
            self._attr_entity_category = EntityCategory(spec.entity_category)
        profile = runtime.profile
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.subentry_id)},
            name=runtime.title,
            manufacturer=BRAND_TITLES[profile.brand],
            model=profile.models[0],
            # cada equipo cuelga del dispositivo de marca
            via_device=(DOMAIN, brand_entry_id),
        )

    @property
    def available(self) -> bool:
        # hasta la primera lectura correcta no hay datos: la entidad nace unavailable
        return super().available and self.coordinator.data is not None
```

`custom_components/modbus_solar/adapters/inbound/entities/factory.py`:

```python
"""Construye las entidades de un equipo a partir de su perfil."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass

from ....domain.profile import EntitySpec
from ....domain.types import Platform
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


class ModbusSolarSensor(ModbusSolarEntity, SensorEntity):
    def __init__(
        self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: EntitySpec, brand_entry_id: str
    ) -> None:
        super().__init__(coordinator, runtime, spec, brand_entry_id)
        # domain guarda cadenas; aquí se convierten a los enums de HA
        if spec.device_class is not None:
            self._attr_device_class = SensorDeviceClass(spec.device_class)
        if spec.state_class is not None:
            self._attr_state_class = SensorStateClass(spec.state_class)
        self._attr_native_unit_of_measurement = spec.unit
        if spec.enum is not None:
            self._attr_options = list(spec.enum.values())

    @property
    def native_value(self) -> int | float | str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.values.get(self._spec.key)


def build_sensors(runtime: DeviceRuntime, brand_entry_id: str) -> list[ModbusSolarSensor]:
    return [
        ModbusSolarSensor(runtime.coordinators[spec.poll], runtime, spec, brand_entry_id)
        for spec in runtime.profile.entities
        if spec.platform is Platform.SENSOR
    ]
```

`custom_components/modbus_solar/sensor.py`:

```python
"""Plataforma sensor: entidades de cada equipo, asociadas a su subentry."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .adapters.inbound.entities.factory import build_sensors
from .adapters.inbound.runtime import ModbusSolarConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: ModbusSolarConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    for subentry_id, runtime in entry.runtime_data.items():
        async_add_entities(build_sensors(runtime, entry.entry_id), config_subentry_id=subentry_id)
```

`custom_components/modbus_solar/__init__.py` (sustituye el contenido):

```python
"""Modbus Solar: raíz de composición. Une catálogo, gateway Modbus y adaptadores de HA."""

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.const import Platform as HaPlatform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams

from .adapters.inbound.runtime import DeviceRuntime, ModbusSolarConfigEntry, build_runtime, enabled_keys
from .adapters.outbound.modbus_gateway import ModbusGateway
from .application.catalog import Catalog
from .const import BRAND_TITLES, CONF_BRAND, CONF_PROFILE, CONF_UNIT_ID, DOMAIN, SUBENTRY_DEVICE
from .profiles import ALL_PROFILES

CATALOG = Catalog(ALL_PROFILES)
PLATFORMS = [HaPlatform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=BRAND_TITLES[entry.data[CONF_BRAND]],
        name=entry.title,
        entry_type=dr.DeviceEntryType.SERVICE,
    )
    registry = er.async_get(hass)
    runtimes: dict[str, DeviceRuntime] = {}
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_DEVICE:
            continue
        data = subentry.data
        profile = CATALOG.get(data[CONF_PROFILE])
        # conexión compartida por endpoint; HA la libera al descargar la entry
        unit = async_get_unit(hass, entry, ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT]), data[CONF_UNIT_ID])
        gateway = ModbusGateway(unit, profile)
        keys = enabled_keys(registry, subentry.subentry_id, profile)
        runtimes[subentry.subentry_id] = build_runtime(hass, entry, subentry, profile, gateway, keys)
    entry.runtime_data = runtimes

    # primer refresh en segundo plano: un equipo caído no retrasa el arranque ni bloquea la entry
    for runtime in runtimes.values():
        for coordinator in runtime.coordinators.values():
            entry.async_create_background_task(hass, coordinator.async_refresh(), f"{coordinator.name} first refresh")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # alta, baja o reconfigure de una subentry: recargar abre y cierra las conexiones necesarias
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar
git commit -m "feat: setup de la entry, entidades sensor y recarga por subentries" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`, con todos los tests de `tests/ha` (Tareas 10-14) en verde.

---

### Tarea 15: Diagnostics

**Files:**
- Create: `custom_components/modbus_solar/adapters/inbound/diagnostics.py`,
  `custom_components/modbus_solar/diagnostics.py`
- Test: `tests/ha/test_diagnostics.py`

**Interfaces:**
- Consumes: `DeviceRuntime` y `ModbusSolarConfigEntry` (Tarea 10); `TierCoordinator.last_error`,
  `last_error_at` y `data` (Tarea 10); `async_redact_data` de `homeassistant.components.diagnostics`.
- Produces: `device_diagnostics(runtime: DeviceRuntime, subentry_data: Mapping[str, Any]) -> dict[str, Any]`,
  con las claves `subentry` (host oculto), `profile`, `intervals`, `tiers` y `entities`.
- Produces: `async_get_config_entry_diagnostics(hass, entry)`, que devuelve `{"devices": {subentry_id: …}}`,
  y `async_get_device_diagnostics(hass, entry, device)`, que devuelve el dict del equipo
  (`{}` para el dispositivo de marca).

- [ ] **Paso 1: Test que falla**

`tests/ha/test_diagnostics.py`:

```python
"""Diagnostics: valores crudos para verificar escala y word_order; host oculto."""

import json
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit

from custom_components.modbus_solar.const import DOMAIN
from custom_components.modbus_solar.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)
from tests.ha.common import DEVICE, DEVICE_ID, brand_entry, setup_entry, tick


async def test_entry_diagnostics(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    device = diagnostics["devices"][DEVICE_ID]
    assert device["subentry"]["host"] == "**REDACTED**"
    assert device["subentry"]["unit_id"] == 1
    assert device["profile"] == "ingeteam.oneplay_storage"
    assert device["intervals"] == {"fast": 5, "normal": 60, "slow": 3600}
    assert set(device["tiers"]) == {"fast", "normal"}
    assert device["tiers"]["fast"] == {"last_update_success": True, "last_error": None, "last_error_at": None}
    assert device["entities"]["active_power"] == {
        "address": 0x1037,
        "dtype": "s32",
        "word_order": "big",
        "scale": 0.1,
        "raw": [0, 12345],
        "value": 1234.5,
    }
    assert device["entities"]["inverter_state"]["value"] == "grid_connected"
    assert "192.168.1.50" not in json.dumps(diagnostics)


async def test_tier_error_is_reported(
    hass: HomeAssistant, patch_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    ingeteam_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    fast = (await async_get_config_entry_diagnostics(hass, entry))["devices"][DEVICE_ID]["tiers"]["fast"]
    assert fast["last_update_success"] is False
    assert fast["last_error"] == "DeviceUnavailable: no route"
    assert fast["last_error_at"] is not None


async def test_device_diagnostics(hass: HomeAssistant, patch_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    await setup_entry(hass, entry)
    devices = dr.async_get(hass)
    device = devices.async_get_device(identifiers={(DOMAIN, DEVICE_ID)})
    brand = devices.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None and brand is not None
    entry_diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert await async_get_device_diagnostics(hass, entry, device) == entry_diagnostics["devices"][DEVICE_ID]
    assert await async_get_device_diagnostics(hass, entry, brand) == {}
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/ha/test_diagnostics.py
git commit -m "test(red): diagnostics" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `ModuleNotFoundError: No module named 'custom_components.modbus_solar.diagnostics'`.

- [ ] **Paso 3: Implementación**

`custom_components/modbus_solar/adapters/inbound/diagnostics.py`:

```python
"""Diagnostics de un equipo: perfil, intervalos, estado de cada tier y palabras crudas."""

from collections.abc import Mapping
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST

from .runtime import DeviceRuntime

TO_REDACT = {CONF_HOST}


def device_diagnostics(runtime: DeviceRuntime, subentry_data: Mapping[str, Any]) -> dict[str, Any]:
    tiers = {
        tier.value: {
            "last_update_success": coordinator.last_update_success,
            "last_error": coordinator.last_error,
            "last_error_at": coordinator.last_error_at.isoformat() if coordinator.last_error_at else None,
        }
        for tier, coordinator in runtime.coordinators.items()
    }
    entities: dict[str, Any] = {}
    for spec in runtime.profile.entities:
        # data guarda el último TierResult correcto, también tras un fallo
        result = runtime.coordinators[spec.poll].data
        raw = result.raw.get(spec.key) if result is not None else None
        reg = spec.register
        entities[spec.key] = {
            "address": reg.address,
            "dtype": reg.dtype.value,
            "word_order": reg.word_order.value,
            "scale": reg.scale,
            "raw": list(raw) if raw is not None else None,
            "value": result.values.get(spec.key) if result is not None else None,
        }
    return {
        "subentry": async_redact_data(dict(subentry_data), TO_REDACT),
        "profile": runtime.profile.id,
        "intervals": runtime.intervals,
        "tiers": tiers,
        "entities": entities,
    }
```

`custom_components/modbus_solar/diagnostics.py`:

```python
"""Diagnostics de la entry de marca y de cada equipo."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .adapters.inbound.diagnostics import device_diagnostics
from .adapters.inbound.runtime import ModbusSolarConfigEntry
from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> dict[str, Any]:
    return {
        "devices": {
            subentry_id: device_diagnostics(runtime, entry.subentries[subentry_id].data)
            for subentry_id, runtime in entry.runtime_data.items()
        }
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ModbusSolarConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    for subentry_id, runtime in entry.runtime_data.items():
        if (DOMAIN, subentry_id) in device.identifiers:
            return device_diagnostics(runtime, entry.subentries[subentry_id].data)
    # dispositivo de marca: no tiene registros propios
    return {}
```

- [ ] **Paso 4: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add custom_components/modbus_solar/adapters/inbound/diagnostics.py custom_components/modbus_solar/diagnostics.py
git commit -m "feat(inbound): diagnostics por equipo y por entry" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `exit 0`.

---

### Tarea 16: Ajustes del repositorio en GitHub

Los checks `description`, `issues` y `topics` de `hacs/action` leen ajustes del repositorio,
no ficheros (spec §7.3). Van antes del primer push de `validate.yml` (Tarea 17).

**Files:** ninguno.

**Interfaces:**
- Produces: repositorio `sigergy/modbus-solar-inverter` con descripción, issues habilitadas y topics.

- [ ] **Paso 1: Pedir confirmación al usuario**

Cambia un recurso externo y visible. Mostrar el comando del paso 2 y esperar el «sí».

- [ ] **Paso 2: Aplicar**

```bash
gh repo edit sigergy/modbus-solar-inverter \
  --description "Home Assistant custom integration for solar inverters over Modbus TCP (HACS)" \
  --enable-issues \
  --add-topic home-assistant --add-topic hacs --add-topic hacs-integration \
  --add-topic modbus --add-topic solar --add-topic ingeteam
```

- [ ] **Paso 3: Verificar**

```bash
gh repo view sigergy/modbus-solar-inverter --json description,hasIssuesEnabled,repositoryTopics
```

Esperado: la descripción del paso 2, `"hasIssuesEnabled": true` y los 6 topics.

---

### Tarea 17: Empaquetado HACS, icono, validación y release

**Files:**
- Create: `hacs.json`, `.github/workflows/validate.yml`, `.github/workflows/release.yml`,
  `custom_components/modbus_solar/brand/icon.png`
- Modify: `README.md`, `tests/unit/test_packaging.py`

**Interfaces:**
- Consumes: `manifest.json` (Tarea 1), con `version` `0.1.0`.
- Produces: `hacs.json` de la spec §8; `validate.yml` con los jobs `hassfest` y `hacs`;
  `release.yml`, que se dispara con los tags `v*.*.*`.

- [ ] **Paso 1: Tests que fallan**

Añadir a `tests/unit/test_packaging.py`:

```python
import struct

ROOT = PACKAGE.parents[1]


def test_hacs_json() -> None:
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs == {
        "name": "Modbus Solar",
        "zip_release": True,
        "filename": "modbus_solar.zip",
        "homeassistant": "2026.9.0",
    }


def test_brand_icon_is_256_png() -> None:
    data = (PACKAGE / "brand" / "icon.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    # cabecera IHDR: ancho y alto en los bytes 16-24
    assert struct.unpack(">II", data[16:24]) == (256, 256)
```

- [ ] **Paso 2: Gates, commit RED y CI**

```bash
bash scripts/lint.sh
git add tests/unit/test_packaging.py
git commit -m "test(red): hacs.json e icono de marca" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh   # run_in_background: true
```

Esperado: `test` en rojo con `FileNotFoundError` de `hacs.json` y de `brand/icon.png`.

- [ ] **Paso 3: `hacs.json` y workflows**

`hacs.json`:

```json
{
  "name": "Modbus Solar",
  "zip_release": true,
  "filename": "modbus_solar.zip",
  "homeassistant": "2026.9.0"
}
```

`.github/workflows/validate.yml`:

```yaml
name: validate

on:
  push:
    branches: [main, "feat/**", "fix/**", "refactor/**", "docs/**"]
  pull_request:

jobs:
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: hacs/action@main
        with:
          category: integration
          # PolyForm Noncommercial no es una licencia aprobada por OSI (ADR 0008)
          ignore: license
```

`.github/workflows/release.yml`:

```yaml
name: release

on:
  push:
    tags: ["v*.*.*"]

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Versión del manifest igual al tag
        run: |
          version="$(jq -r .version custom_components/modbus_solar/manifest.json)"
          test "v${version}" = "${GITHUB_REF_NAME}" || { echo "manifest ${version} != tag ${GITHUB_REF_NAME}"; exit 1; }
      - name: Empaquetar
        working-directory: custom_components/modbus_solar
        run: zip -r ../../modbus_solar.zip . -x "__pycache__/*" "*/__pycache__/*"
      - name: Publicar release
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh release create "${GITHUB_REF_NAME}" modbus_solar.zip --generate-notes
```

El zip contiene el contenido de la carpeta, sin la carpeta: HACS lo descomprime dentro de
`custom_components/modbus_solar/`.

- [ ] **Paso 4: Icono**

Script de un solo uso en `%TEMP%`; no se commitea. Dibuja un sol con una onda: sin marcas de
Home Assistant (spec §8).

`$TEMP/make_icon.py`:

```python
"""Genera brand/icon.png: 256x256, fondo transparente, sol y onda de señal."""

import math
import sys

from PIL import Image, ImageDraw

size, scale = 256, 4  # se dibuja a 1024 px y se reduce para suavizar bordes
big = size * scale
img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
sun, wave = (245, 166, 35, 255), (33, 120, 200, 255)
cx, cy, r = big // 2, big * 2 // 5, big // 6
draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=sun)
for i in range(8):
    a = i * math.pi / 4
    x1, y1 = cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35
    x2, y2 = cx + math.cos(a) * r * 1.85, cy + math.sin(a) * r * 1.85
    draw.line((x1, y1, x2, y2), fill=sun, width=big // 28)
points = [(x, big * 0.82 + math.sin(x / big * 4 * math.pi) * big * 0.07) for x in range(big // 10, big * 9 // 10)]
draw.line(points, fill=wave, width=big // 22, joint="curve")
img.resize((size, size), Image.LANCZOS).save(sys.argv[1])
```

```bash
.venv/Scripts/python -m pip install -q pillow
mkdir -p custom_components/modbus_solar/brand
.venv/Scripts/python "$TEMP/make_icon.py" custom_components/modbus_solar/brand/icon.png
rm "$TEMP/make_icon.py"
```

- [ ] **Paso 5: README**

`README.md` (sustituye el contenido):

```markdown
# Modbus Solar

Custom integration de Home Assistant para inversores solares por Modbus TCP.
Usa la conexión compartida de la integración `modbus` del core.

## Equipos soportados

| Marca | Modelo | Entidades |
|---|---|---|
| Ingeteam | 1Play Storage | estado del inversor, potencia activa, energía total |

## Requisitos

- Home Assistant 2026.9.0 o posterior.
- El equipo accesible por Modbus TCP. El Ingeteam admite un solo cliente Modbus a la vez.

## Instalación

1. HACS → Integraciones → menú → Repositorios personalizados.
2. Añadir `https://github.com/sigergy/modbus-solar-inverter`, categoría «Integration».
3. Instalar «Modbus Solar» y reiniciar Home Assistant.

## Configuración

1. Ajustes → Dispositivos y servicios → Añadir integración → «Modbus Solar».
2. Elegir la marca. Se crea una entrada por marca.
3. En la entrada, «Añadir equipo»: nombre, host, puerto, ID de unidad y modelo.
   La integración lee el estado del inversor antes de guardar.
4. «Reconfigurar» en el equipo cambia host, puerto e intervalos de sondeo.

Detalle: [docs/features/device-setup.md](docs/features/device-setup.md) y
[docs/features/monitoring.md](docs/features/monitoring.md).

## Licencia

[PolyForm Noncommercial License 1.0.0](LICENSE)
```

- [ ] **Paso 6: Gates, commit GREEN y CI**

```bash
bash scripts/lint.sh
git add hacs.json .github/workflows/validate.yml .github/workflows/release.yml custom_components/modbus_solar/brand README.md
git commit -m "build: empaquetado HACS, icono, validate y release" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh             # run_in_background: true
bash scripts/ci-wait.sh validate.yml  # run_in_background: true
```

Esperado: `exit 0` en los dos. Si `hacs` falla en `description`, `issues` o `topics`, falta la Tarea 16.
`release.yml` no se ejecuta aquí: se prueba con el primer tag, tras el merge.

---

### Tarea 18: Wiki de Ingeteam

**Files:**
- Create: `docs/wiki/brands/ingeteam/README.md`, `docs/wiki/brands/ingeteam/AAA0030IMB03_N.pdf`,
  `docs/wiki/brands/ingeteam/1-play-tl-m/ACL2010IMB05.pdf`,
  `docs/wiki/brands/ingeteam/1-play-tl-m/registers.md`
- Delete: carpeta vacía `docs/wiki/brands/ingeteam/1_3-play/` (no está en la spec §9)

**Interfaces:**
- Produces: fuente de los registros que cita `profiles/ingeteam/oneplay_storage.py`.

- [ ] **Paso 1: Comprobar que las carpetas de destino están vacías**

```bash
find docs/wiki -type f
```

Esperado: ninguna salida. Si aparece algún fichero, parar y preguntar al usuario antes de seguir.

- [ ] **Paso 2: Copiar los PDF y comprobar los SHA-256**

```bash
src="/c/Users/carlo/OneDrive/My_Projects/Domotica/Solar/Ingeteam"
cp "$src/Write_REG_Modbus_1P-Storage-AAA0030IMB03_.pdf" docs/wiki/brands/ingeteam/AAA0030IMB03_N.pdf
cp "$src/Input_REG_Modbus_1P-Storage-ACL2010IMB05_.pdf" docs/wiki/brands/ingeteam/1-play-tl-m/ACL2010IMB05.pdf
sha256sum docs/wiki/brands/ingeteam/AAA0030IMB03_N.pdf docs/wiki/brands/ingeteam/1-play-tl-m/ACL2010IMB05.pdf
rmdir docs/wiki/brands/ingeteam/1_3-play
```

Esperado (spec §9):

```
b53eb0c3ad36230365833a798429e1e0d3be3ed8488e361fb70ceb1ee4c1d332  docs/wiki/brands/ingeteam/AAA0030IMB03_N.pdf
c0e6533edbd194974aba3e9fc3f040a65e009cabdd143aea6a02e6b2578620d4  docs/wiki/brands/ingeteam/1-play-tl-m/ACL2010IMB05.pdf
```

Si un hash no coincide, parar y preguntar.

- [ ] **Paso 3: `README.md` de la marca**

`docs/wiki/brands/ingeteam/README.md`:

```markdown
# Ingeteam: documentación Modbus

Solo PDF oficiales y públicos de Ingeteam (ADR 0006).

| Fichero | Documento | Revisión | SHA-256 | Obtenido |
|---|---|---|---|---|
| `AAA0030IMB03_N.pdf` | Comandos Modbus, genérico de marca (original `Write_REG_Modbus_1P-Storage-AAA0030IMB03_.pdf`) | N, 20/05/24 | `b53eb0c3ad36230365833a798429e1e0d3be3ed8488e361fb70ceb1ee4c1d332` | 2026-10-04 |
| `1-play-tl-m/ACL2010IMB05.pdf` | Input registers 1Play Storage (original `Input_REG_Modbus_1P-Storage-ACL2010IMB05_.pdf`) | IMB05 | `c0e6533edbd194974aba3e9fc3f040a65e009cabdd143aea6a02e6b2578620d4` | 2026-10-04 |

- La revisión F de AAA0030IMB03 (09/02/18) es anterior y se descarta.
- Falta `ACL0000IMC01` (estados y eventos). Se pide a Ingeteam.
- Tabla de registros extraída: [1-play-tl-m/registers.md](1-play-tl-m/registers.md).
```

- [ ] **Paso 4: `registers.md`**

Extraer el texto del PDF con su paginación:

```bash
pdftotext -layout docs/wiki/brands/ingeteam/1-play-tl-m/ACL2010IMB05.pdf "$TEMP/acl.txt"
```

`pdftotext` separa las páginas con el carácter `\f`. Con ese texto, escribir
`docs/wiki/brands/ingeteam/1-play-tl-m/registers.md` así:

```markdown
# 1Play Storage: input registers (ACL2010IMB05)

Extraído de `ACL2010IMB05.pdf`. Ante discrepancia, manda el PDF.
Escala `[X x 10]` y orden de palabras de los registros de 32 bits sin verificar en equipo:
se comprueban con diagnostics.

| Dirección | Nombre (PDF) | Tipo | Unidad | Página | Notas |
|---|---|---|---|---|---|
```

Reglas de la tabla:
- Una fila por registro del PDF, en el orden del PDF. Dirección en hexadecimal (`0x101D`),
  y nombre, tipo y unidad copiados literalmente.
- `Página` es el número de página del PDF (posición del `\f` + 1).
- `Notas`: referencias a notas al pie del PDF (por ejemplo, «Nota 3»), literales.
- Después de la tabla, una sección `## Notas del PDF` con el texto de cada nota, literal.
- No se interpreta ni se completa nada que el PDF no diga.

Comprobar que las tres filas que usa el perfil coinciden con
`profiles/ingeteam/oneplay_storage.py`:

```bash
grep -nE "0x101D|0x1021|0x1037" docs/wiki/brands/ingeteam/1-play-tl-m/registers.md
```

Esperado: tres filas. `0x101D` en la página 7 con la Nota 3; `0x1021` en Wh x 10 y 32 bits;
`0x1037` en W x 10 y 32 bits con signo. Si alguna discrepa del perfil, parar y preguntar.

- [ ] **Paso 5: Commit**

```bash
rm "$TEMP/acl.txt"
git add docs/wiki
git commit -m "docs(wiki): PDF oficiales de Ingeteam y tabla de registros" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
git push -q origin HEAD
```

---

### Tarea 19: ADR, arquitectura y guías

**Files:**
- Create: `docs/README.md`, `docs/decisions/0001-hexagonal-import-linter.md` … `0008-license-polyform-noncommercial.md`,
  `docs/architecture/overview.md`, `domain.md`, `application.md`, `ports.md`,
  `docs/architecture/adapters/inbound.md`, `outbound.md`,
  `docs/guides/setup.md`, `testing.md`, `release.md`

**Interfaces:**
- Consumes: el código de las Tareas 1-17. Cada afirmación sobre el código cita `archivo:línea`
  del código ya commiteado.

Plantilla de cada ADR:

```markdown
---
status: accepted
date: 2026-10-04
---

# NNNN — Título

## Contexto

## Decisión

## Consecuencias
```

- [ ] **Paso 1: ADR**

Un fichero por decisión, con este contenido en cada sección:

| ADR | Contexto | Decisión | Consecuencias |
|---|---|---|---|
| `0001-hexagonal-import-linter.md` · Hexagonal estricto con import-linter | Las integraciones de HA mezclan protocolo, lógica y entidades. Se quieren tests sin HA para la lógica. | Capas `domain`, `ports`, `application` y `adapters`, más `profiles`. Contratos en `pyproject.toml` (`[tool.importlinter]`), verificados por `lint-imports` en CI. | `domain`, `ports`, `application` y `profiles` no importan `homeassistant` ni `modbus_connection`. La raíz del paquete compone. Un import prohibido rompe el job `lint`. |
| `0002-python-profiles.md` · Perfiles en Python | Cada equipo necesita registros, escalas, tiers y metadatos de entidad. | Perfiles como `DeviceProfile` en `profiles/<marca>/`. Validados por `validate_profile` en tests. | Sin parser ni esquema JSON en esta fase. SunSpec por escaneo, en la spec 3. Exportar e importar JSON, en la última fase. |
| `0003-modbus-shared-connection.md` · Conexión compartida del core | El Ingeteam admite un solo cliente Modbus. HA 2026.9 expone `async_get_unit` y `async_get_temporary_unit`. | Conexión vía `homeassistant.components.modbus` y `modbus-connection`. Sin pymodbus directo. `requirements: []` en el manifest. | Varias entries comparten conexión por endpoint. El espaciado entre peticiones lo aplica `set_message_spacing`. Tests con `modbus_connection.mock`. |
| `0004-entry-brand-subentry-device.md` · Entry = marca, subentry = equipo | Se quieren varios equipos de una marca bajo un mismo punto. | Una config entry por marca (`unique_id` = marca). Cada equipo es una subentry `device` (`unique_id` = `host:puerto:unidad`). | Alta, baja o reconfigure de un equipo recarga la entry de marca entera. Aceptable: son operaciones raras. |
| `0005-poll-tiers.md` · Tiers de sondeo | Hay valores que cambian cada segundo y otros cada hora. | Tres tiers, `fast`, `normal` y `slow`, de 5, 60 y 3600 s. Un coordinator por tier. Editables en reconfigure, con mínimo `min_tier_interval` del perfil. | Las entidades deshabilitadas no se leen. Un intervalo menor que el tiempo de lectura del tier se rechaza en el formulario. |
| `0006-vendor-docs-official-only.md` · Solo PDF oficiales | La documentación de fabricantes circula en copias no oficiales. | En `docs/wiki/brands/` solo entran PDF oficiales y públicos, con SHA-256 y revisión. | Un registro sin fuente oficial no entra en un perfil. |
| `0007-tests-ci-only.md` · Tests solo en CI | La máquina de desarrollo es Windows y HA no se instala allí. | `pytest` solo en GitHub Actions. En local, solo `scripts/lint.sh` (ruff, lint-imports, compileall). | TDD con commits `test(red)` empujados y esperados con `scripts/ci-wait.sh`. Cada ciclo cuesta minutos de CI. |
| `0008-license-polyform-noncommercial.md` · PolyForm Noncommercial 1.0.0 | Proyecto sin uso comercial previsto. | `LICENSE` PolyForm Noncommercial 1.0.0 con `Required Notice`. | Se puede relajar a AGPL-3.0 más adelante, no endurecer: las versiones publicadas conservan su licencia. `hacs/action` ignora el check `license` (no es OSI). |

- [ ] **Paso 2: Arquitectura**

Cada fichero describe el código final y cita `archivo:línea`:
- `overview.md`:
  - diagrama de capas en texto;
  - contratos de import-linter, con cita a `pyproject.toml`;
  - flujo de datos: setup → `async_get_unit` → `ModbusGateway` → `TierCoordinator` → `read_tier` → `decode` → entidad;
  - composición en `__init__.py` y `config_flow.py`.
- `domain.md`: `types`, `profile`, `errors`, `decode`, `blocks` y `validate`. Una línea de propósito y la firma pública de cada uno.
- `application.md`:
  - `Catalog`, `read_tier`, `TierResult`, `min_tier_interval` y `probe_device`;
  - qué errores propaga cada uno.
- `ports.md`: protocolo `DeviceGateway` y su contrato. Devuelve palabras por `RegisterSpec`, y lanza `DeviceUnavailable` o `DeviceProtocolError`.
- `adapters/inbound.md`:
  - flows y sus errores;
  - `TierCoordinator`, `DeviceRuntime` y entidades;
  - formatos de `unique_id`;
  - diagnostics.
- `adapters/outbound.md`:
  - `ModbusGateway`: bloques, `set_message_spacing` y traducción de excepciones de `modbus_connection`.

- [ ] **Paso 3: Guías**

- `guides/setup.md`:
  - clonar;
  - `py -3.13 -m venv .venv`;
  - instalar ruff e import-linter;
  - `bash scripts/lint.sh`;
  - por qué no hay pytest local (ADR 0007);
  - el Ingeteam admite un solo cliente Modbus: si otro cliente (por ejemplo, el EMS) ocupa
    el puerto, el equipo sale `unavailable` y se reintenta en el siguiente tick (spec §5).
- `guides/testing.md`:
  - `tests/unit` frente a `tests/ha`;
  - fixtures `ingeteam_unit`, `temp_unit` y `patch_unit`;
  - `FakeGateway`;
  - ciclo RED/GREEN con `scripts/ci-wait.sh`;
  - pines del job `test`, copiados de `.github/workflows/tests.yml`.
- `guides/release.md`:
  1. subir `version` en `manifest.json`;
  2. merge a `main`;
  3. `git tag vX.Y.Z` y push del tag;
  4. `release.yml` comprueba la versión y adjunta `modbus_solar.zip`.

- [ ] **Paso 4: Índice**

`docs/README.md`:

```markdown
# Documentación

| Carpeta | Contenido |
|---|---|
| [architecture/](architecture/overview.md) | Capas, reglas de dependencia y flujo de datos. Viva. |
| [decisions/](decisions/) | ADR inmutables, numerados. |
| [changes/](changes/) | Un directorio por cambio: `spec.md` y `plan.md`. |
| [research/](research/) | Análisis previos. |
| [guides/](guides/) | Setup, tests y release. |
| [features/](features/) | Qué hace cada funcionalidad. Viva. |
| [wiki/](wiki/brands/) | Documentación oficial de fabricantes. |

Flujo: `research/` → `decisions/` → `changes/` → al cerrar, `features/`, `architecture/` y `guides/`.

## Cambios

| Cambio | Estado |
|---|---|
| [2026-10-04-skeleton](changes/2026-10-04-skeleton/spec.md) | en curso |
```

- [ ] **Paso 5: Commit**

```bash
git add docs/README.md docs/decisions docs/architecture docs/guides
git commit -m "docs: ADR 0001-0008, arquitectura y guías" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
git push -q origin HEAD
```

---

### Tarea 20: Cierre de la spec 0

Paso 4 del flujo de `docs/` (spec §9, «Tarea de cierre»).

**Files:**
- Create: `docs/features/device-setup.md`, `docs/features/monitoring.md`
- Modify: `docs/changes/2026-10-04-skeleton/spec.md` (front-matter), `docs/README.md`,
  y `docs/architecture/` o `docs/guides/` si el código cambió tras la Tarea 19

**Interfaces:**
- Consumes: textos de `strings.json` (Tarea 11), perfil Ingeteam (Tarea 6) y diagnostics (Tarea 15).

- [ ] **Paso 1: `features/device-setup.md`**

Contenido, con los nombres de campo y error de `strings.json`:
- Alta de la marca: una entry por marca; repetir la marca aborta con `already_configured`.
- Alta del equipo: campos `name`, `host`, `port` (por defecto 502), `unit_id` (por defecto 1, rango 1-247) y `profile`.
- La sonda lee la entidad `probe_key` del perfil antes de guardar.
- Errores:
  - `cannot_connect`: el equipo no responde;
  - `endpoint_in_use`: endpoint usado con otros parámetros de enlace;
  - `invalid_response`: excepción Modbus o valor fuera del enum;
  - abort `already_configured`: mismo `host:port:unit_id`.
- Reconfigure:
  - cambia `host`, `port` e intervalos;
  - no cambia `unit_id` ni el modelo;
  - `interval_too_short` si un intervalo es menor que el tiempo de lectura del tier (Ingeteam: fast ≥ 2 s, normal ≥ 1 s).
- Intervalos por defecto: 5, 60 y 3600 s.

- [ ] **Paso 2: `features/monitoring.md`**

Contenido:
- Tabla de sensores (clave, nombre, unidad, tier, registro):
  - `inverter_state`: enum, fast, `0x101D`;
  - `active_power`: W, fast, `0x1037`;
  - `total_energy`: Wh, normal, `0x1021`, `total_increasing`.
- Disponibilidad:
  - las entidades de un tier pasan a `unavailable` si su lectura falla, y vuelven en la siguiente lectura correcta;
  - un equipo caído al arrancar no bloquea la entry.
- Un valor fuera del enum deja el resto del tier en pie y avisa una vez en el log.
- Panel de Energía: `total_energy` como producción solar.
- Diagnostics: cómo descargarlo y qué muestra (`raw`, `scale` y `word_order`, para verificar las escalas `[X x 10]` en la VM).

- [ ] **Paso 3: Revisar `architecture/` y `guides/`**

```bash
git diff --stat <commit de la Tarea 19>..HEAD -- custom_components .github scripts
```

Si hay cambios, actualizar las citas `archivo:línea` afectadas.

- [ ] **Paso 4: Marcar el cambio como cerrado**

- En `docs/changes/2026-10-04-skeleton/spec.md`, front-matter: `status: draft` → `status: done`.
- En `docs/README.md`, fila del cambio: `en curso` → `cerrado`.

- [ ] **Paso 5: Gates finales, commit y CI**

```bash
bash scripts/lint.sh
git add docs
git commit -m "docs: cierre de la spec 0 (features, estado done)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QpFWCyFiYdpk1gwMN8wMX5"
bash scripts/ci-wait.sh               # run_in_background: true
bash scripts/ci-wait.sh validate.yml  # run_in_background: true
```

Esperado: `exit 0` en los dos. Después, `finishing-a-development-branch`: el merge a `main`
pide confirmación al usuario.
