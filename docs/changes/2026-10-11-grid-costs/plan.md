---
type: feature
area: energy
layers: [domain, application, adapters, profiles]
status: draft
date: 2026-10-11
---

# Plan de implementación — Costes de red en el STORAGE 1Play TL M

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `subagent-driven-development` (recomendada) o `executing-plans`
> para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** implementar la [spec](spec.md). Pasos «Costes de red» y «Precios» en el alta y en reconfigurar. Precio
fijo o dinámico por sentido. Sensores «Coste de la energía importada» y «Coste de la energía exportada» en el
dispositivo de las energías de red.

**Arquitectura:** hexagonal, vigilada por import-linter. El dominio gana `domain/cost.py` (precio y acumulador),
`FlowSpec.cost_key/cost_role` y `DerivedCostSpec`. `application/selection.py` crea los costes del modo si la entry
guarda `costs`. Los adaptadores crean el sensor, limpian el registro y añaden los pasos del flujo. `domain`, `ports`,
`application` y `profiles` no importan HA.

**Stack:** Python 3.14, Home Assistant 2026.9.4, pytest con `pytest-homeassistant-custom-component` (solo en CI),
ruff (línea de 120), import-linter, hassfest y HACS en `validate.yml`.

Rutas de código relativas a `custom_components/modbus_solar/` salvo indicación.

## Global Constraints

- Rama `feat/grid-costs` (contiene spec y plan). Sin worktree. Push a esa rama con `bash scripts/ci-wait.sh` solo
  con autorización del usuario. Force push, merge, rebase y PR piden confirmación.
- Tests solo en CI: nunca `pytest` en local (falta `modbus_connection`). El gate local es `bash scripts/lint.sh`
  antes de cada commit.
- Cada tarea: commit `test(red): …` con los tests que fallan (CI en rojo por esos tests y solo esos). Después,
  commit `feat: …` con CI en verde. Si un test(red) no puede ni importar (símbolo nuevo), el rojo es el error de
  import de ese fichero: vale.
- Trailer obligatorio en cada commit:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01XbPbmatF9duX3B2i74fSpz
  ```
- Comentarios en español; identificadores, ficheros y tests en inglés. Dentro del paquete, solo imports relativos.
- Antes de orientarse, `graft ask "<pregunta>" --source` o `graft grep "<símbolo>"`; antes de cambiar una firma,
  `graft callers <símbolo> --depth 2`. `graft/` y `.graft_*` no se commitean nunca.
- `VERSION` del flujo sigue en 2; sin migración (spec §4). Una entry sin `costs` funciona igual que hoy.
- Con el seguimiento desactivado, la clave `costs` **no se guarda** (ni `None`): el alta no la escribe y reconfigurar
  la quita. `test_reconfigure_four_steps` compara `entry.data` exacto y debe seguir pasando sin cambios.
- Forma de `entry.data["costs"]`, literal:
  `{"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "dynamic", "entity_id": "sensor.x"}}`.
- Unidades del precio dinámico: `€/kWh`, `EUR/kWh` (factor 1) y `€/MWh`, `EUR/MWh` (factor 0,001).
- Sensor de coste: `device_class` `monetary`, unidad `EUR`, `state_class` `total`, precisión 2.
- Nombres: `grid_import_cost` «Coste de la energía importada» / «Grid import cost»; `grid_export_cost` «Coste de la
  energía exportada» / «Grid export cost».
- `en.json` es copia literal de `strings.json`; `es.json` tiene las mismas claves (`tests/unit/test_translations.py`).
- No inventar: si una API (de HA o del código) no se comporta como dice el plan, parar y avisar con la salida real.
  Las citas `archivo:línea` son de `82944fa`; tras cada tarea pueden moverse.

## Mapa de ficheros

| Fichero | Cambio | Tarea |
|---|---|---|
| `domain/cost.py` | nuevo: `PRICE_UNITS`, `price_per_kwh`, `CostAccumulator` | 1 |
| `domain/types.py` | roles `COST_GRID_IMPORT`, `COST_GRID_EXPORT` | 2 |
| `domain/metering.py` | `FlowSpec.cost_key/cost_role`, `DerivedCostSpec` | 2 |
| `domain/validate.py` | `_metering_problems` revisa `cost_key` | 2 |
| `application/selection.py` | `Selection.costs`, `select(..., costs)` | 3 |
| `profiles/ingeteam/oneplay_storage.py` | `cost_key`/`cost_role` en `GRID_FLOWS` | 3 |
| `const.py` | `CONF_COSTS` | 4 |
| `adapters/inbound/entities/cost.py` | nuevo: `ModbusSolarCostSensor` | 4 |
| `adapters/inbound/entities/base.py` | acepta `DerivedCostSpec` | 4 |
| `adapters/inbound/entities/factory.py` | crea los sensores de coste | 4 |
| `adapters/inbound/runtime.py` | `DeviceRuntime.costs`; `enabled_keys` y `always_update` con costes | 4 |
| `__init__.py` | `select` con `costs`; limpieza del registro | 4 |
| `strings.json`, `translations/*.json` | entidades (T4); pasos, selector y error (T5) | 4, 5 |
| `adapters/inbound/flow.py` | pasos `costs`, `cost_prices` (T5); reconfigurar y `entity_list` (T6) | 5, 6 |
| `tests/unit/test_cost.py` | nuevo | 1 |
| `tests/unit/test_validate.py` | tests de `cost_key` | 2 |
| `tests/unit/test_selection.py` | `metered()` con costes; tests de `select` | 3 |
| `tests/unit/test_storage_profile.py` | flujos con coste | 3 |
| `tests/unit/test_translations.py` | entidades, pasos, selector y error | 4, 5 |
| `tests/ha/common.py` | `setup_storage_entry(..., costs=)` | 4 |
| `tests/ha/test_cost.py` | nuevo | 4 |
| `tests/ha/test_init.py` | limpieza al quitar `costs` | 4 |
| `tests/ha/test_config_flow.py` | pasos nuevos; tests existentes pasan por `costs` | 5, 6 |
| `docs/…`, `CHANGELOG.md` | docs vivas, changelog, `status: done` | 7 |

---

### Task 1: Dominio del coste

**Files:**
- Create: `domain/cost.py`
- Test: `tests/unit/test_cost.py`

**Interfaces:**
- Consumes: `EnergyAccumulator(sign, max_gap_s)` y `SignFilter` de `domain/energy.py:9-58`.
- Produces:
  - `PRICE_UNITS: dict[str, float]` (unidad → factor a €/kWh).
  - `price_per_kwh(value: object, unit: str | None) -> float | None`.
  - `CostAccumulator(sign: SignFilter, max_gap_s: float, total_eur: float = 0.0)`, propiedad `total_eur: float`,
    método `add(t: float, power_w: float | None, price: float | None) -> None`.

- [ ] **Step 1: Escribir los tests que fallan**

`tests/unit/test_cost.py`:

```python
"""Coste de la energía: precio en €/kWh y acumulado en euros con energía pendiente."""

import pytest

from custom_components.modbus_solar.domain.cost import CostAccumulator, price_per_kwh
from custom_components.modbus_solar.domain.energy import SignFilter


def test_price_units() -> None:
    assert price_per_kwh(0.15, "€/kWh") == 0.15
    assert price_per_kwh(0.15, "EUR/kWh") == 0.15
    assert price_per_kwh(120, "€/MWh") == pytest.approx(0.12)
    assert price_per_kwh("120", "EUR/MWh") == pytest.approx(0.12)


def test_price_unknown_unit() -> None:
    for unit in (None, "€", "c€/kWh", "kWh", "€/Wh"):
        assert price_per_kwh(0.15, unit) is None, unit


def test_price_not_numeric() -> None:
    for value in ("unavailable", "unknown", "", None, True, float("nan"), "nan", float("inf"), "-inf", object()):
        assert price_per_kwh(value, "€/kWh") is None, value


def test_negative_price_is_valid() -> None:
    # hay horas con precio negativo en el mercado
    assert price_per_kwh("-0.01", "€/kWh") == -0.01


def run(acc: CostAccumulator, *samples: tuple[float, float | None, float | None]) -> float:
    for t, power, price in samples:
        acc.add(t, power, price)
    return acc.total_eur


def test_cost_with_price() -> None:
    # 2 kWh a 0,2 €/kWh
    assert run(CostAccumulator(SignFilter.POSITIVE, 7200), (0, 1000, 0.2), (3600, 3000, 0.2)) == pytest.approx(0.4)


def test_cost_follows_the_sign() -> None:
    assert run(CostAccumulator(SignFilter.NEGATIVE, 7200), (0, -1800, 0.05), (3600, -1800, 0.05)) == pytest.approx(
        0.09
    )
    assert run(CostAccumulator(SignFilter.NEGATIVE, 60), (0, 500, 0.05), (10, 500, 0.05)) == 0


def test_each_sample_uses_its_price() -> None:
    acc = CostAccumulator(SignFilter.POSITIVE, 7200)
    # 1,8 kWh a 0,1 y luego 1,8 kWh a 0,3
    assert run(acc, (0, 3600, 0.1), (1800, 3600, 0.1)) == pytest.approx(0.18)
    assert run(acc, (3600, 3600, 0.3)) == pytest.approx(0.72)


def test_energy_without_price_is_charged_with_the_next_price() -> None:
    acc = CostAccumulator(SignFilter.POSITIVE, 7200)
    assert run(acc, (0, 3600, 0.1), (1800, 3600, None)) == 0
    # los 1,8 kWh pendientes y los 1,8 kWh nuevos, a 0,2
    assert run(acc, (3600, 3600, 0.2)) == pytest.approx(0.72)


def test_gaps_and_missing_power_are_not_charged() -> None:
    acc = CostAccumulator(SignFilter.POSITIVE, 15)
    assert run(acc, (0, 3600, 0.1), (20, 3600, 0.1)) == 0
    assert run(acc, (30, 3600, 0.1)) == pytest.approx(0.001)
    cut = CostAccumulator(SignFilter.POSITIVE, 60)
    assert run(cut, (0, 3600, 0.1), (10, None, 0.1), (20, 3600, 0.1)) == 0


def test_restored_total_can_go_down_with_negative_price() -> None:
    acc = CostAccumulator(SignFilter.POSITIVE, 7200, total_eur=1.5)
    assert run(acc, (0, 1000, -0.1), (3600, 1000, -0.1)) == pytest.approx(1.4)
```

- [ ] **Step 2: Lint y commit del rojo**

Run: `bash scripts/lint.sh`
Expected: sin errores (los tests importan un módulo que aún no existe; ruff no lo comprueba).

```bash
git add tests/unit/test_cost.py
git commit -m "test(red): coste de la energía en el dominio"
```

Si el usuario autorizó el push: `bash scripts/ci-wait.sh`. Expected: CI en rojo solo por
`ModuleNotFoundError: ... domain.cost` en `tests/unit/test_cost.py`.

- [ ] **Step 3: Implementación mínima**

`domain/cost.py`:

```python
"""Coste de la energía: precio en €/kWh y euros acumulados sobre la energía integrada."""

import math

from .energy import EnergyAccumulator, SignFilter

# unidades aceptadas del precio y su factor a €/kWh
PRICE_UNITS = {"€/kWh": 1.0, "EUR/kWh": 1.0, "€/MWh": 0.001, "EUR/MWh": 0.001}


def price_per_kwh(value: object, unit: str | None) -> float | None:
    """Precio en €/kWh. None si el valor no es numérico o la unidad no es de energía en euros."""
    factor = None if unit is None else PRICE_UNITS.get(unit)
    # bool es int en Python: un True no es un precio
    if factor is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return None
    else:
        return None
    if not math.isfinite(number):
        return None
    return number * factor


class CostAccumulator:
    """Acumula euros: la energía de cada muestra por el precio de esa muestra.

    Sin precio, la energía queda pendiente y se cobra con el siguiente precio válido.
    El total puede bajar: un precio negativo es válido.
    """

    def __init__(self, sign: SignFilter, max_gap_s: float, total_eur: float = 0.0) -> None:
        self._energy = EnergyAccumulator(sign, max_gap_s)
        self._total_eur = total_eur
        # no se persiste: si HA se reinicia con el precio caído, ese tramo queda sin coste
        self._pending_kwh = 0.0

    @property
    def total_eur(self) -> float:
        return self._total_eur

    def add(self, t: float, power_w: float | None, price: float | None) -> None:
        before = self._energy.total_kwh
        self._energy.add(t, power_w)
        self._pending_kwh += self._energy.total_kwh - before
        if price is not None:
            self._total_eur += self._pending_kwh * price
            self._pending_kwh = 0.0
```

- [ ] **Step 4: Lint y commit del verde**

Run: `bash scripts/lint.sh`
Expected: sin errores, import-linter `Contracts: N kept, 0 broken`.

```bash
git add custom_components/modbus_solar/domain/cost.py
git commit -m "feat: precio por kWh y acumulador de coste"
```

Con push: `bash scripts/ci-wait.sh`. Expected: CI en verde.

---

### Task 2: Tipos de coste y validación del perfil

**Files:**
- Modify: `domain/types.py:71-75`, `domain/metering.py:9-38`, `domain/validate.py:70-96`
- Test: `tests/unit/test_validate.py`

**Interfaces:**
- Consumes: `SignFilter`, `Role`, `Component`.
- Produces:
  - `Role.COST_GRID_IMPORT = "cost_grid_import"`, `Role.COST_GRID_EXPORT = "cost_grid_export"`.
  - `FlowSpec.cost_key: str | None = None`, `FlowSpec.cost_role: Role | None = None`.
  - `DerivedCostSpec(key, role, source, sign, component, direction, enabled_default=True)`, `frozen`, `kw_only`.
  - Mensajes de validación: `"metering {mode}: cost_key and cost_role go together"`; las `cost_key` usan los mismos
    mensajes que las demás claves de flujo (`"duplicate key: {key}"`, `"metering: {key} differs between modes"`).

- [ ] **Step 1: Tests que fallan**

Añadir al final de `tests/unit/test_validate.py` (ya importa `replace`, `Role`, `SignFilter`, `FlowSpec` y tiene
`flow`, `mode`, `with_modes` en las líneas 273-292):

```python
def costed(cost_key: str = "c_in", role: Role = Role.COST_GRID_IMPORT) -> FlowSpec:
    return replace(flow(), cost_key=cost_key, cost_role=role)


def test_metering_cost_key_is_a_flow_key() -> None:
    assert validate_profile(with_modes(mode("x", flows=(costed(),)))) == []
    # choca con la potencia del mismo flujo
    assert validate_profile(with_modes(mode("x", flows=(costed("p_in"),)))) == [
        "duplicate key: p_in",
        "metering: p_in differs between modes",
    ]
    other = mode("y", flows=(costed(role=Role.COST_GRID_EXPORT),))
    assert validate_profile(with_modes(mode("x", flows=(costed(),)), other)) == [
        "metering: c_in differs between modes"
    ]


def test_metering_cost_key_and_role_go_together() -> None:
    assert validate_profile(with_modes(mode("x", flows=(replace(flow(), cost_key="c_in"),)))) == [
        "metering x: cost_key and cost_role go together"
    ]
    assert validate_profile(with_modes(mode("x", flows=(replace(flow(), cost_role=Role.COST_GRID_IMPORT),)))) == [
        "metering x: cost_key and cost_role go together"
    ]
```

Comprobar con `grep -n "^from\|^import" tests/unit/test_validate.py` que `replace` y `Role` ya se importan; si
falta alguno, añadirlo al bloque de imports existente.

- [ ] **Step 2: Lint y commit del rojo**

Run: `bash scripts/lint.sh`

```bash
git add tests/unit/test_validate.py
git commit -m "test(red): cost_key en los flujos de medición"
```

Con push, expected: rojo por `TypeError: ... unexpected keyword argument 'cost_key'` (o `AttributeError` de
`Role.COST_GRID_IMPORT`) solo en esos dos tests.

- [ ] **Step 3: Implementación**

`domain/types.py`, tras `ENERGY_GENERATOR = "energy_generator"`:

```python
    # coste de la energía de red (seguimiento de costes)
    COST_GRID_IMPORT = "cost_grid_import"
    COST_GRID_EXPORT = "cost_grid_export"
```

`domain/metering.py`, en `FlowSpec` tras `sign: SignFilter`:

```python
    # coste del sentido; None = sin coste (el generador)
    cost_key: str | None = None
    cost_role: Role | None = None
```

y cambiar su docstring a `"""Un sentido del intercambio: su potencia derivada, la energía que la integra y su coste."""`.

`domain/metering.py`, al final:

```python
@dataclass(frozen=True, kw_only=True)
class DerivedCostSpec:
    """Coste calculado: la energía de la fuente filtrada por signo, por el precio de su sentido."""

    key: str  # también translation_key y sufijo del unique_id
    role: Role
    source: str  # la misma fuente de potencia que su energía
    sign: SignFilter
    component: Component
    direction: str  # "import" o "export": clave de su precio en entry.data["costs"]
    enabled_default: bool = True
```

`domain/validate.py`, en `_metering_problems`, sustituir el bucle `for flow in mode.flows:` (líneas 89-95) por:

```python
        for flow in mode.flows:
            if (flow.cost_key is None) != (flow.cost_role is None):
                problems.append(f"metering {mode.key}: cost_key and cost_role go together")
            keys = [(flow.power_key, flow.power_role), (flow.energy_key, flow.energy_role)]
            if flow.cost_key is not None and flow.cost_role is not None:
                keys.append((flow.cost_key, flow.cost_role))
            for key, role in keys:
                if key in seen or key in mode_keys:
                    problems.append(f"duplicate key: {key}")
                mode_keys.add(key)
                if flow_keys.setdefault(key, (role, flow.sign)) != (role, flow.sign):
                    problems.append(f"metering: {key} differs between modes")
```

- [ ] **Step 4: Lint y commit del verde**

Run: `bash scripts/lint.sh`

```bash
git add custom_components/modbus_solar/domain/types.py custom_components/modbus_solar/domain/metering.py custom_components/modbus_solar/domain/validate.py
git commit -m "feat: cost_key en FlowSpec y DerivedCostSpec"
```

Con push, expected: CI en verde.

---

### Task 3: Selección de costes y perfil STORAGE

**Files:**
- Modify: `application/selection.py:13-70`, `profiles/ingeteam/oneplay_storage.py:173-188`
- Test: `tests/unit/test_selection.py`, `tests/unit/test_storage_profile.py`

**Interfaces:**
- Consumes: `DerivedCostSpec`, `FlowSpec.cost_key/cost_role` (Task 2).
- Produces:
  - `Selection.costs: tuple[DerivedCostSpec, ...] = ()`.
  - `select(profile, components, metering=None, costs: Mapping[str, Any] | None = None) -> Selection`. Con `costs`
    vacío o `None`, `Selection.costs == ()`.
  - `COST_DIRECTIONS = {SignFilter.POSITIVE: "import", SignFilter.NEGATIVE: "export"}` en `application/selection.py`.
  - Perfil: claves `grid_import_cost` (`Role.COST_GRID_IMPORT`) y `grid_export_cost` (`Role.COST_GRID_EXPORT`).

- [ ] **Step 1: Tests que fallan**

`tests/unit/test_selection.py`: en `metered()`, añadir a los dos `FlowSpec` de `grid` (líneas 46-59)
`cost_key="in_c", cost_role=Role.COST_GRID_IMPORT` y `cost_key="out_c", cost_role=Role.COST_GRID_EXPORT`
respectivamente. Después, al final del fichero:

```python
COSTS = {"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "fixed", "price": 0.05}}


def test_select_without_costs_has_no_costs() -> None:
    assert select(metered(), [], None).costs == ()
    assert select(metered(), [], None, None).costs == ()


def test_select_adds_costs_of_the_mode() -> None:
    selection = select(metered(), [], "internal", COSTS)
    assert [(c.key, c.role, c.source, c.sign, c.component, c.direction) for c in selection.costs] == [
        ("in_c", Role.COST_GRID_IMPORT, "m", SignFilter.POSITIVE, Component.INTERNAL_METER, "import"),
        ("out_c", Role.COST_GRID_EXPORT, "m", SignFilter.NEGATIVE, Component.INTERNAL_METER, "export"),
    ]


def test_island_has_no_costs() -> None:
    # el flujo del generador no declara coste
    assert select(metered(), [], "island", COSTS).costs == ()
```

`tests/unit/test_storage_profile.py`, en `test_metering_modes` (líneas ~187-222): ampliar cada tupla de `grid` con
la clave y el rol de coste, la de `generator` con `None, None`, y la comprensión de `modes`:

```python
    grid = [
        (
            "grid_import_power",
            Role.GRID_IMPORT_POWER,
            "grid_import_energy",
            Role.ENERGY_GRID_IMPORT,
            SignFilter.POSITIVE,
            "grid_import_cost",
            Role.COST_GRID_IMPORT,
        ),
        (
            "grid_export_power",
            Role.GRID_EXPORT_POWER,
            "grid_export_energy",
            Role.ENERGY_GRID_EXPORT,
            SignFilter.NEGATIVE,
            "grid_export_cost",
            Role.COST_GRID_EXPORT,
        ),
    ]
    generator = [
        (
            "generator_power",
            Role.GENERATOR_POWER,
            "generator_energy",
            Role.ENERGY_GENERATOR,
            SignFilter.POSITIVE,
            None,
            None,
        )
    ]
    modes = [
        (
            m.key,
            m.source,
            m.component,
            [(f.power_key, f.power_role, f.energy_key, f.energy_role, f.sign, f.cost_key, f.cost_role) for f in m.flows],
        )
        for m in PROFILE.metering_modes
    ]
```

Y al final del fichero:

```python
def test_costs_follow_the_grid_meter() -> None:
    costs = {"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "fixed", "price": 0.05}}
    on_grid = select(PROFILE, None, "grid_loads", costs)
    assert [(c.key, c.source, c.component) for c in on_grid.costs] == [
        ("grid_import_cost", "grid_power", Component.GRID),
        ("grid_export_cost", "grid_power", Component.GRID),
    ]
    internal = select(PROFILE, None, "critical_loads", costs)
    assert {(c.source, c.component) for c in internal.costs} == {("internal_meter_power", Component.INTERNAL_METER)}
    assert select(PROFILE, None, "off_grid", costs).costs == ()
```

- [ ] **Step 2: Lint y commit del rojo**

Run: `bash scripts/lint.sh`

```bash
git add tests/unit/test_selection.py tests/unit/test_storage_profile.py
git commit -m "test(red): costes en la selección y en el perfil STORAGE"
```

Con push, expected: rojo por `TypeError: select() takes ... positional arguments` y `AttributeError: ... 'costs'`
en los tests nuevos, y por la comparación de tuplas en `test_metering_modes`.

- [ ] **Step 3: Implementación**

`application/selection.py`:

```python
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from ..domain.control import GatedLimitSpec
from ..domain.energy import EnergySpec, SignFilter
from ..domain.metering import DerivedCostSpec, DerivedPowerSpec, MeteringModeSpec
...

# sentido del precio de cada signo: lo que entra se compra, lo que sale se vende
COST_DIRECTIONS = {SignFilter.POSITIVE: "import", SignFilter.NEGATIVE: "export"}


@dataclass(frozen=True)
class Selection:
    entities: tuple[EntitySpec, ...]
    energies: tuple[EnergySpec, ...]
    controls: tuple[GatedLimitSpec, ...]
    powers: tuple[DerivedPowerSpec, ...] = ()  # potencias derivadas del modo de medición
    costs: tuple[DerivedCostSpec, ...] = ()  # costes del modo; vacío sin seguimiento de costes
```

En `select`, nueva firma y cálculo de los costes dentro de `if mode is not None:` tras `mode_energies`:

```python
def select(
    profile: DeviceProfile,
    components: Collection[Component] | None,
    metering: str | None = None,
    costs: Mapping[str, Any] | None = None,
) -> Selection:
    """costs es entry.data["costs"]; None o vacío = sin seguimiento de costes."""
    chosen = chosen_components(profile, components, metering)
    mode = metering_mode(profile, metering)
    powers: tuple[DerivedPowerSpec, ...] = ()
    mode_energies: tuple[EnergySpec, ...] = ()
    mode_costs: tuple[DerivedCostSpec, ...] = ()
    if mode is not None:
        # ... powers y mode_energies sin cambios ...
        if costs:
            # el coste integra la misma fuente y signo que su energía
            mode_costs = tuple(
                DerivedCostSpec(
                    key=f.cost_key,
                    role=f.cost_role,
                    source=mode.source,
                    sign=f.sign,
                    component=mode.component,
                    direction=COST_DIRECTIONS[f.sign],
                )
                for f in mode.flows
                if f.cost_key is not None and f.cost_role is not None
            )
    return Selection(
        entities=...,  # sin cambios
        energies=...,
        controls=...,
        powers=powers,
        costs=mode_costs,
    )
```

`profiles/ingeteam/oneplay_storage.py`, en `GRID_FLOWS`: añadir `cost_key="grid_import_cost",
cost_role=Role.COST_GRID_IMPORT` al flujo `POSITIVE` y `cost_key="grid_export_cost", cost_role=Role.COST_GRID_EXPORT`
al `NEGATIVE`.

- [ ] **Step 4: Lint y commit del verde**

Run: `bash scripts/lint.sh`

```bash
git add custom_components/modbus_solar/application/selection.py custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py
git commit -m "feat: select crea los costes del modo de medición"
```

Con push, expected: CI en verde. Ojo: `test_every_entity_and_enum_state_is_translated` aún no recorre `cost_key`;
lo amplía la Task 4.

---

### Task 4: Sensor de coste, runtime, arranque y nombres

**Files:**
- Create: `adapters/inbound/entities/cost.py`, `tests/ha/test_cost.py`
- Modify: `const.py`, `adapters/inbound/entities/base.py:40-58`, `adapters/inbound/entities/factory.py:38-53`,
  `adapters/inbound/runtime.py:19-113`, `__init__.py:28-82`, `strings.json`, `translations/en.json`,
  `translations/es.json`
- Test: `tests/ha/common.py:60-83`, `tests/ha/test_init.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: `CostAccumulator`, `price_per_kwh` (Task 1); `DerivedCostSpec` (Task 2); `select(..., costs)` y
  `Selection.costs` (Task 3).
- Produces:
  - `CONF_COSTS = "costs"` en `const.py`.
  - `DeviceRuntime.costs: Mapping[str, Any] | None = None` (copia de `entry.data["costs"]`).
  - `ModbusSolarCostSensor(coordinator, runtime, spec: DerivedCostSpec, price: Mapping[str, Any])`.
  - `setup_storage_entry(..., costs: dict[str, Any] | None = None)` en `tests/ha/common.py`.

- [ ] **Step 1: Tests que fallan**

`tests/ha/common.py`, en `setup_storage_entry`: nuevo parámetro `costs: dict[str, Any] | None = None` tras
`metering`, y tras el bloque de `metering`:

```python
    if costs is not None:
        data["costs"] = costs
```

`tests/ha/test_cost.py`:

```python
"""Sensores de coste de red del STORAGE: precio fijo, dinámico, caído y restaurado."""

import logging
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import async_fire_time_changed, mock_restore_cache_with_extra_data

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE_ID, STORAGE_DATA, device_entry, entity_id_of, setup_storage_entry, state_of

FIXED = {"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "fixed", "price": 0.05}}
DYNAMIC = {"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "dynamic", "entity_id": "sensor.price"}}
# la red exporta 300 W (fixture storage_unit)
EXPORTED_6S = 300 * 6 / 3_600_000


async def advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def euros(hass: HomeAssistant, key: str) -> float:
    return float(state_of(hass, key).state)


async def test_cost_sensors_on_the_grid_device(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, None, costs=FIXED)
    for key in ("grid_import_cost", "grid_export_cost"):
        cost = state_of(hass, key)
        attributes = cost.attributes
        assert (attributes["unit_of_measurement"], attributes["device_class"], attributes["state_class"]) == (
            "EUR",
            "monetary",
            "total",
        )
        entity = er.async_get(hass).async_get(entity_id_of(hass, key))
        device = dr.async_get(hass).async_get(entity.device_id)
        assert device.identifiers == {(DOMAIN, f"{DEVICE_ID}_grid")}


async def test_entry_without_costs_has_no_cost_sensors(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, None)
    assert entity_id_of(hass, "grid_import_cost") is None
    assert entity_id_of(hass, "grid_export_cost") is None


async def test_off_grid_has_no_cost_sensors(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, None, metering="off_grid", costs=FIXED)
    assert entity_id_of(hass, "grid_import_cost") is None


async def test_fixed_price(hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, None, costs=FIXED)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_export_cost") == pytest.approx(EXPORTED_6S * 0.05)
    assert euros(hass, "grid_import_cost") == 0


async def test_import_cost_on_the_internal_meter(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    # el vatímetro interno (30052) mide 600 W entrando
    storage_unit.input[51] = 600
    await setup_storage_entry(hass, None, metering="critical_loads", costs=FIXED)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_import_cost") == pytest.approx(600 * 6 / 3_600_000 * 0.15)
    entity = er.async_get(hass).async_get(entity_id_of(hass, "grid_import_cost"))
    device = dr.async_get(hass).async_get(entity.device_id)
    assert device.identifiers == {(DOMAIN, f"{DEVICE_ID}_internal_meter")}


async def test_dynamic_price_in_mwh(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    hass.states.async_set("sensor.price", "120", {"unit_of_measurement": "€/MWh"})
    await setup_storage_entry(hass, None, costs=DYNAMIC)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_export_cost") == pytest.approx(EXPORTED_6S * 0.12)


async def test_unavailable_price_keeps_energy_pending(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    patch_storage_unit: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hass.states.async_set("sensor.price", "unavailable", {"unit_of_measurement": "€/kWh"})
    await setup_storage_entry(hass, None, costs=DYNAMIC)
    await advance(hass, freezer, 6)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_export_cost") == 0
    # un aviso por caída, no por muestra
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and "sensor.price" in r.getMessage()]
    assert len(warnings) == 1
    hass.states.async_set("sensor.price", "0.1", {"unit_of_measurement": "€/kWh"})
    await advance(hass, freezer, 6)
    # los 12 s pendientes y los 6 s nuevos, a 0,1
    assert euros(hass, "grid_export_cost") == pytest.approx(3 * EXPORTED_6S * 0.1)


async def test_cost_restored_after_restart(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    # la entidad se crea antes con un entity_id fijo para no depender del nombre del dispositivo
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{DEVICE_ID}_grid_export_cost", suggested_object_id="inverter_grid_export_cost"
    )
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("sensor.inverter_grid_export_cost", "1.5"),
                {"native_value": 1.5, "native_unit_of_measurement": "EUR"},
            )
        ],
    )
    await setup_storage_entry(hass, None, costs=FIXED)
    assert entity_id_of(hass, "grid_export_cost") == "sensor.inverter_grid_export_cost"
    assert euros(hass, "grid_export_cost") == 1.5


async def test_cost_reads_its_source_with_power_and_energy_disabled(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    entry = device_entry({**STORAGE_DATA, "costs": FIXED})
    entry.add_to_hass(hass)
    keys = ("grid_power", "grid_import_power", "grid_export_power", "grid_import_energy", "grid_export_energy")
    for key in keys:
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"{DEVICE_ID}_{key}", config_entry=entry, disabled_by=er.RegistryEntryDisabler.USER
        )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_export_cost") == pytest.approx(EXPORTED_6S * 0.05)
```

`tests/ha/test_init.py`, al final (usa `setup_storage_entry` y `entity_id_of` de `tests.ha.common`; añadirlos al
import si faltan):

```python
async def test_removing_costs_removes_cost_sensors(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    costs = {"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "fixed", "price": 0.05}}
    entry = await setup_storage_entry(hass, None, costs=costs)
    assert entity_id_of(hass, "grid_import_cost") is not None
    hass.config_entries.async_update_entry(entry, data={k: v for k, v in entry.data.items() if k != "costs"})
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entity_id_of(hass, "grid_import_cost") is None
    assert entity_id_of(hass, "grid_export_cost") is None
```

`tests/unit/test_translations.py`, en `test_every_entity_and_enum_state_is_translated` (líneas 50-52), tras la
comprobación de `flow.energy_key`:

```python
                if flow.cost_key is not None:
                    assert "name" in entities["sensor"][flow.cost_key], flow.cost_key
```

Y un test nuevo tras `test_metering_entity_names`:

```python
def test_cost_entity_names() -> None:
    expected = {
        "strings.json": {"grid_import_cost": "Grid import cost", "grid_export_cost": "Grid export cost"},
        "translations/es.json": {
            "grid_import_cost": "Coste de la energía importada",
            "grid_export_cost": "Coste de la energía exportada",
        },
    }
    for name, names in expected.items():
        sensors = load(name)["entity"]["sensor"]
        assert {key: sensors[key]["name"] for key in names} == names, name
```

- [ ] **Step 2: Lint y commit del rojo**

Run: `bash scripts/lint.sh`

```bash
git add tests/ha/common.py tests/ha/test_cost.py tests/ha/test_init.py tests/unit/test_translations.py
git commit -m "test(red): sensores de coste de red"
```

Con push, expected: rojo en los tests nuevos (no hay sensores `grid_*_cost`; faltan las traducciones) y en
`test_every_entity_and_enum_state_is_translated` (`KeyError: 'grid_import_cost'`). Ninguno más.

- [ ] **Step 3: Implementación**

`const.py`, tras `CONF_METERING`:

```python
# seguimiento de costes de red; ausente = sin costes
CONF_COSTS = "costs"
```

`adapters/inbound/entities/base.py`: importar `DerivedCostSpec` junto a `DerivedPowerSpec` y ampliar la unión de
`spec` a `EntitySpec | EnergySpec | GatedLimitSpec | DerivedPowerSpec | DerivedCostSpec`.

`adapters/inbound/entities/cost.py`:

```python
"""Sensor de coste: la energía de su fuente por el precio fijo o el de una entidad de HA."""

import logging
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from ....domain.cost import CostAccumulator, price_per_kwh
from ....domain.metering import DerivedCostSpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity

_LOGGER = logging.getLogger(__name__)


class ModbusSolarCostSensor(ModbusSolarEntity, RestoreSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    # HA no admite total_increasing con monetary; además un precio negativo resta
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "EUR"
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: DerivedCostSpec, price: Mapping[str, Any]
    ) -> None:
        super().__init__(coordinator, runtime, spec)
        self._cost = spec
        self._price = price
        # tres intervalos sin muestra = hueco que no se cobra, como la energía
        self._max_gap_s = 3 * runtime.intervals[coordinator.tier]
        self._accumulator = CostAccumulator(spec.sign, self._max_gap_s)
        self._price_missing = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and isinstance(last.native_value, int | float | Decimal):
            self._accumulator = CostAccumulator(self._cost.sign, self._max_gap_s, float(last.native_value))
        self._sample()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sample()
        super()._handle_coordinator_update()

    def _sample(self) -> None:
        price = self._current_price()
        # un aviso por caída del precio, no por muestra
        if price is None and not self._price_missing:
            _LOGGER.warning(
                "%s: price from %s unavailable; the energy stays pending", self.entity_id, self._price.get("entity_id")
            )
        elif price is not None and self._price_missing:
            _LOGGER.info("%s: price from %s back", self.entity_id, self._price.get("entity_id"))
        self._price_missing = price is None
        self._accumulator.add(dt_util.utcnow().timestamp(), self._source_power(), price)

    def _current_price(self) -> float | None:
        if self._price["mode"] == "fixed":
            return float(self._price["price"])
        state = self.hass.states.get(self._price["entity_id"])
        if state is None:
            return None
        return price_per_kwh(state.state, state.attributes.get("unit_of_measurement"))

    def _source_power(self) -> float | None:
        data = self.coordinator.data
        if not self.coordinator.last_update_success or data is None:
            return None
        value = data.values.get(self._cost.source)
        # una fuente sin valor (decode o lectura fallida) corta la serie
        return float(value) if isinstance(value, int | float) else None

    @property
    def native_value(self) -> float:
        return self._accumulator.total_eur
```

`adapters/inbound/entities/factory.py`: importar `ModbusSolarCostSensor` de `.cost` y, al final de
`build_sensors` antes del `return`:

```python
    prices = runtime.costs or {}
    for cost in runtime.selection.costs:
        # el coste se actualiza con el coordinator de su fuente, como la potencia derivada
        coordinator = runtime.coordinators[by_key[cost.source].poll]
        sensors.append(ModbusSolarCostSensor(coordinator, runtime, cost, prices[cost.direction]))
```

`adapters/inbound/runtime.py`:

- importar `Mapping` y `Any`, y `CONF_COSTS` de `...const`;
- en `DeviceRuntime`, tras `serial_number`:
  ```python
      costs: Mapping[str, Any] | None = None  # precios de entry.data["costs"]; None sin seguimiento
  ```
- en `enabled_keys`, tras el bucle de `powers`:
  ```python
      costs = selection.costs if isinstance(selection, Selection) else ()
      for cost in costs:
          # un coste activo necesita leer su fuente aunque su potencia y su energía estén deshabilitadas
          if _is_enabled(registry, Platform.SENSOR, entry_id, cost.key, cost.enabled_default):
              keys.add(cost.source)
  ```
- en `build_runtime`, `energy_tiers` incluye las fuentes de los costes (integran aunque la potencia no cambie):
  ```python
      energy_tiers = {poll_of[source] for energy in selection.energies for source in energy.sources}
      energy_tiers |= {poll_of[cost.source] for cost in selection.costs}
  ```
- en el `DeviceRuntime(...)` de `build_runtime`: `costs=entry.data.get(CONF_COSTS),`.

`__init__.py`:

- importar `CONF_COSTS`;
- en `_remove_unselected`, `flow_keys` suma las `cost_key`:
  ```python
      flow_keys = {key for mode in modes for flow in mode.flows for key in (flow.power_key, flow.energy_key)}
      flow_keys |= {flow.cost_key for mode in modes for flow in mode.flows if flow.cost_key is not None}
  ```
  y `kept` suma `| {c.key for c in selection.costs}`;
- en `async_setup_entry`: `selection = select(profile, requested, metering, data.get(CONF_COSTS))`.

`strings.json` y `translations/en.json`, en `entity.sensor`, tras `generator_energy`:

```json
      "grid_import_cost": { "name": "Grid import cost" },
      "grid_export_cost": { "name": "Grid export cost" },
```

`translations/es.json`, mismo sitio:

```json
      "grid_import_cost": { "name": "Coste de la energía importada" },
      "grid_export_cost": { "name": "Coste de la energía exportada" },
```

Respetar el formato del fichero (indentación y forma de las entradas vecinas).

- [ ] **Step 4: Lint y commit del verde**

Run: `bash scripts/lint.sh`

```bash
git add custom_components/modbus_solar/const.py custom_components/modbus_solar/adapters/inbound/entities/cost.py custom_components/modbus_solar/adapters/inbound/entities/base.py custom_components/modbus_solar/adapters/inbound/entities/factory.py custom_components/modbus_solar/adapters/inbound/runtime.py custom_components/modbus_solar/__init__.py custom_components/modbus_solar/strings.json custom_components/modbus_solar/translations/en.json custom_components/modbus_solar/translations/es.json
git commit -m "feat: sensores de coste de la energía de red"
```

Con push, expected: CI en verde. Si `test_import_cost_on_the_internal_meter` falla porque 600 en 30052 no es
importación, **parar y avisar**: el signo de 30052 no está verificado en el equipo (spec, hechos de partida).

---

### Task 5: Pasos de costes en el alta

**Files:**
- Modify: `adapters/inbound/flow.py` (imports, constantes, `DeviceConfigFlow` estado y pasos de alta,
  `_show_intervals`, `async_step_readings`, `async_step_intervals`), `strings.json`, `translations/*.json`
- Test: `tests/ha/test_config_flow.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: `PRICE_UNITS` (Task 1); `select(..., costs)` (Task 3); `CONF_COSTS` (Task 4).
- Produces (módulo `flow.py`):
  - constantes `CONF_ENABLED = "enabled"`, `COST_DIRECTIONS = ("import", "export")`, `MODE_FIXED = "fixed"`,
    `MODE_DYNAMIC = "dynamic"`;
  - `has_costs(profile: DeviceProfile, metering: str | None) -> bool`;
  - `costs_schema(stored: Mapping[str, Any] | None) -> vol.Schema`;
  - `cost_prices_schema(modes: Mapping[str, str]) -> vol.Schema`;
  - `cost_prices_suggested(modes: Mapping[str, str], stored: Mapping[str, Any] | None) -> dict[str, Any]`;
  - `price_errors(hass: HomeAssistant, modes: Mapping[str, str], user_input: Mapping[str, Any]) -> dict[str, str]`;
  - `costs_data(modes: Mapping[str, str], user_input: Mapping[str, Any]) -> dict[str, Any]`;
  - estado del flujo `_costs: dict[str, Any] | None` y `_cost_modes: dict[str, str]`;
  - métodos `_after_metering()`, `_show_costs(step_id, stored)`, `_show_cost_prices(step_id, stored, errors, typed)`;
  - pasos `async_step_costs`, `async_step_cost_prices`.
  - `_show_intervals(..., costs: Mapping[str, Any] | None)`: parámetro nuevo tras `metering`.

- [ ] **Step 1: Tests que fallan**

`tests/ha/test_config_flow.py`:

1. Helper `to_components` (líneas 90-95): pasa por `costs` sin activarlo.

```python
async def to_costs(hass: HomeAssistant, metering: str = "grid_loads") -> dict[str, Any]:
    """Alta del STORAGE hasta el paso de costes de red."""
    result = await configure(hass, await to_metering(hass), {"metering": metering})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "costs")
    return result


async def to_components(hass: HomeAssistant, metering: str = "grid_loads") -> dict[str, Any]:
    """Alta del STORAGE hasta el paso de componentes, sin seguimiento de costes."""
    if metering == "off_grid":
        result = await configure(hass, await to_metering(hass), {"metering": metering})
    else:
        result = await configure(hass, await to_costs(hass, metering), {"enabled": False})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "components")
    return result
```

2. Líneas 382-383 y 397-398 (volver a `model` y a `connection`): entre el `configure` de `metering` y el
   `assert result["step_id"] == "components"`, insertar:

```python
    assert result["step_id"] == "costs"
    result = await configure(hass, result, {"enabled": False})
```

3. Tests nuevos, tras `to_storage_intervals`:

```python
FIXED_COSTS = {"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "fixed", "price": 0.05}}


async def finish_storage(hass: HomeAssistant, result: dict[str, Any]) -> dict[str, Any]:
    """Del paso de componentes al final del alta, con Red y batería."""
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "components")
    result = await configure(hass, result, {"components": ["grid", "battery"]})
    result = await choose(hass, result, "name")
    result = await configure(hass, result, {"name": "House", "device_id": 0})
    return await create(hass, result, STORAGE_INTERVALS)


async def test_costs_off_by_default(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_costs(hass)
    assert field(result, "enabled").default() is False
    assert field(result, "import_mode").default() == "fixed"
    assert field(result, "export_mode").default() == "fixed"
    result = await finish_storage(hass, await configure(hass, result, {}))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "costs" not in result["data"]


async def test_costs_fixed_and_dynamic_are_saved(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    hass.states.async_set("sensor.pvpc", "0.1", {"unit_of_measurement": "€/kWh"})
    result = await to_costs(hass)
    result = await configure(hass, result, {"enabled": True, "import_mode": "fixed", "export_mode": "dynamic"})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "cost_prices")
    assert [str(k) for k in result["data_schema"].schema] == ["import_price", "export_entity"]
    result = await configure(hass, result, {"import_price": 0.15, "export_entity": "sensor.pvpc"})
    result = await finish_storage(hass, result)
    assert result["data"]["costs"] == {
        "import": {"mode": "fixed", "price": 0.15},
        "export": {"mode": "dynamic", "entity_id": "sensor.pvpc"},
    }


async def test_dynamic_price_needs_an_energy_price_unit(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    hass.states.async_set("sensor.temperature", "21", {"unit_of_measurement": "°C"})
    # el estado no se valida: puede estar caído al configurar
    hass.states.async_set("sensor.omie", "unavailable", {"unit_of_measurement": "€/MWh"})
    result = await to_costs(hass)
    result = await configure(hass, result, {"enabled": True, "import_mode": "dynamic", "export_mode": "dynamic"})
    result = await configure(hass, result, {"import_entity": "sensor.temperature", "export_entity": "sensor.omie"})
    assert (result["step_id"], result["errors"]) == ("cost_prices", {"import_entity": "price_unit_invalid"})
    result = await configure(hass, result, {"import_entity": "sensor.missing", "export_entity": "sensor.omie"})
    assert result["errors"] == {"import_entity": "price_unit_invalid"}
    result = await configure(hass, result, {"import_entity": "sensor.omie", "export_entity": "sensor.omie"})
    assert result["step_id"] == "components"


async def test_off_grid_skips_costs(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await configure(hass, await to_metering(hass), {"metering": "off_grid"})
    assert result["step_id"] == "components"
```

`tests/unit/test_translations.py`, en `test_flow_steps_errors_and_aborts_are_translated`: añadir `"costs"` y
`"cost_prices"` al conjunto de pasos y `"price_unit_invalid"` al de errores. Y un test nuevo:

```python
def test_cost_steps_and_modes_are_translated() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        data = load(name)
        steps = data["config"]["step"]
        assert set(steps["costs"]["data"]) == {"enabled", "import_mode", "export_mode"}, name
        assert set(steps["cost_prices"]["data"]) == {"import_price", "export_price", "import_entity", "export_entity"}
        assert set(data["selector"]["cost_mode"]["options"]) == {"fixed", "dynamic"}, name
        assert data["config"]["error"]["price_unit_invalid"], name
    assert load("translations/es.json")["selector"]["cost_mode"]["options"] == {
        "fixed": "Precio fijo",
        "dynamic": "Precio dinámico (entidad)",
    }
```

- [ ] **Step 2: Lint y commit del rojo**

Run: `bash scripts/lint.sh`

```bash
git add tests/ha/test_config_flow.py tests/unit/test_translations.py
git commit -m "test(red): pasos de costes en el alta"
```

Con push, expected: rojo en los tests nuevos, en los que pasan por `to_components` con modo de red y en los dos de
volver atrás (`step_id` es `components`, no `costs`). Los de reconfigurar siguen en verde.

- [ ] **Step 3: Implementación en `flow.py`**

Imports: añadir `BooleanSelector`, `EntitySelector`, `EntitySelectorConfig` al bloque de
`homeassistant.helpers.selector`; `CONF_COSTS` al de `...const`; `from ...domain.cost import PRICE_UNITS`.

Constantes, tras `PROBE_TIMEOUT_S`:

```python
# seguimiento de costes de red (spec 7.3)
CONF_ENABLED = "enabled"
COST_DIRECTIONS = ("import", "export")
MODE_FIXED = "fixed"
MODE_DYNAMIC = "dynamic"
PRICE = NumberSelector(
    NumberSelectorConfig(min=0, max=10, step=0.0001, unit_of_measurement="€/kWh", mode=NumberSelectorMode.BOX)
)
```

Funciones de módulo, tras `check_intervals`:

```python
def has_costs(profile: DeviceProfile, metering: str | None) -> bool:
    """El modo tiene algún flujo con coste: «Aislada» no."""
    mode = metering_mode(profile, metering)
    return mode is not None and any(flow.cost_key is not None for flow in mode.flows)


def costs_schema(stored: Mapping[str, Any] | None) -> vol.Schema:
    """Casilla y modo de cada sentido. Por defecto, lo guardado; sin nada, desactivado y fijo."""
    selector = SelectSelector(
        SelectSelectorConfig(
            options=[MODE_FIXED, MODE_DYNAMIC], mode=SelectSelectorMode.DROPDOWN, translation_key="cost_mode"
        )
    )
    fields: dict[Any, Any] = {vol.Required(CONF_ENABLED, default=stored is not None): BooleanSelector()}
    for direction in COST_DIRECTIONS:
        default = MODE_FIXED if stored is None else stored[direction]["mode"]
        fields[vol.Required(f"{direction}_mode", default=default)] = selector
    return vol.Schema(fields)


def cost_prices_schema(modes: Mapping[str, str]) -> vol.Schema:
    """Un campo por sentido: precio si es fijo, entidad si es dinámico."""
    fields: dict[Any, Any] = {}
    for direction in COST_DIRECTIONS:
        if modes[direction] == MODE_FIXED:
            fields[vol.Required(f"{direction}_price")] = PRICE
        else:
            fields[vol.Required(f"{direction}_entity")] = EntitySelector(EntitySelectorConfig(domain="sensor"))
    return vol.Schema(fields)


def cost_prices_suggested(modes: Mapping[str, str], stored: Mapping[str, Any] | None) -> dict[str, Any]:
    """Valores guardados de los sentidos que conservan su modo."""
    suggested: dict[str, Any] = {}
    for direction in COST_DIRECTIONS:
        saved = (stored or {}).get(direction, {})
        if saved.get("mode") != modes[direction]:
            continue
        if modes[direction] == MODE_FIXED:
            suggested[f"{direction}_price"] = saved["price"]
        else:
            suggested[f"{direction}_entity"] = saved["entity_id"]
    return suggested


def price_errors(hass: HomeAssistant, modes: Mapping[str, str], user_input: Mapping[str, Any]) -> dict[str, str]:
    """Cada entidad dinámica debe existir con unidad €/kWh o €/MWh. Su estado no se mira: puede estar caído."""
    errors: dict[str, str] = {}
    for direction in COST_DIRECTIONS:
        if modes[direction] != MODE_DYNAMIC:
            continue
        key = f"{direction}_entity"
        state = hass.states.get(user_input[key])
        if state is None or state.attributes.get("unit_of_measurement") not in PRICE_UNITS:
            errors[key] = "price_unit_invalid"
    return errors


def costs_data(modes: Mapping[str, str], user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Lo que se guarda en entry.data["costs"]."""
    data: dict[str, Any] = {}
    for direction in COST_DIRECTIONS:
        if modes[direction] == MODE_FIXED:
            data[direction] = {"mode": MODE_FIXED, "price": float(user_input[f"{direction}_price"])}
        else:
            data[direction] = {"mode": MODE_DYNAMIC, "entity_id": user_input[f"{direction}_entity"]}
    return data
```

Estado en `DeviceConfigFlow`, tras `_metering`:

```python
    # costes elegidos (entry.data["costs"]); None = sin seguimiento
    _costs: dict[str, Any] | None = None
    # modo (fixed o dynamic) de cada sentido, entre los pasos costs y cost_prices
    _cost_modes: dict[str, str] = {}
```

Los costes eran del modelo: en `async_step_model` (junto a `self._metering = None`, línea ~344) y en
`_switch_profile` (línea ~373) añadir `self._costs = None`.

`async_step_metering` pasa por `costs` si el modo lo admite:

```python
    async def async_step_metering(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        profile = self._profile
        if user_input is not None:
            self._metering = user_input[CONF_METERING]
            if has_costs(profile, self._metering):
                return await self.async_step_costs()
            self._costs = None
            return await self._after_metering()
        return self._show_metering("metering", profile, self._metering)

    async def _after_metering(self) -> ConfigFlowResult:
        if self._profile.components:
            return await self.async_step_components()
        self._components = []
        return await self.async_step_readings()

    async def async_step_costs(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            if not user_input[CONF_ENABLED]:
                self._costs = None
                return await self._after_metering()
            self._cost_modes = {d: user_input[f"{d}_mode"] for d in COST_DIRECTIONS}
            return await self.async_step_cost_prices()
        return self._show_costs("costs", self._costs)

    async def async_step_cost_prices(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = price_errors(self.hass, self._cost_modes, user_input)
            if not errors:
                self._costs = costs_data(self._cost_modes, user_input)
                return await self._after_metering()
        return self._show_cost_prices("cost_prices", self._costs, errors, user_input)

    def _show_costs(self, step_id: str, stored: Mapping[str, Any] | None) -> ConfigFlowResult:
        """Casilla y modos. Lo comparten el alta y reconfigure."""
        return self.async_show_form(
            step_id=step_id,
            data_schema=costs_schema(stored),
            description_placeholders={"model": self._profile.models[0]},
        )

    def _show_cost_prices(
        self,
        step_id: str,
        stored: Mapping[str, Any] | None,
        errors: dict[str, str],
        typed: Mapping[str, Any] | None,
    ) -> ConfigFlowResult:
        """Precios según el modo de cada sentido. Tras un error conserva lo escrito."""
        suggested = dict(typed) if typed is not None else cost_prices_suggested(self._cost_modes, stored)
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(cost_prices_schema(self._cost_modes), suggested),
            errors=errors,
        )
```

Pasar los costes a `select` en el alta:

- `async_step_readings` (línea ~545): `select(self._profile, self._components or [], self._metering, self._costs)`.
- `_show_intervals`: nuevo parámetro `costs: Mapping[str, Any] | None` justo tras `metering`; dentro,
  `selection = select(profile, components, metering, costs)`.
- `async_step_intervals`: `tiers = present_tiers(select(profile, components, self._metering, self._costs))`; tras
  `data[CONF_METERING] = mode.key`:
  ```python
                if self._costs is not None:
                    data[CONF_COSTS] = self._costs
  ```
  y en su llamada a `_show_intervals`, `self._costs` tras `self._metering`.
- `async_step_reconfigure_intervals`: en su llamada a `_show_intervals`, `self._costs` tras `self._metering` (la
  Task 6 completa reconfigurar).

- [ ] **Step 4: Traducciones**

`strings.json` y `translations/en.json` (copia literal), en `config.step`, tras `metering`:

```json
      "costs": {
        "title": "Grid costs",
        "description": "{model}. Track what the energy bought from and sold to the grid costs. Each direction has its own price: fixed, or read from a Home Assistant entity.",
        "data": {
          "enabled": "Track costs",
          "import_mode": "Import price",
          "export_mode": "Export price"
        },
        "submit": "Next"
      },
      "cost_prices": {
        "title": "Prices",
        "description": "Fixed prices in €/kWh. A price entity must be in €/kWh or €/MWh.",
        "data": {
          "import_price": "Import price",
          "export_price": "Export price",
          "import_entity": "Import price entity",
          "export_entity": "Export price entity"
        },
        "submit": "Next"
      },
```

En `config.error`: `"price_unit_invalid": "The entity must be in €/kWh or €/MWh."`.
En `selector`: `"cost_mode": { "options": { "fixed": "Fixed price", "dynamic": "Dynamic price (entity)" } }`.

`translations/es.json`, mismas claves:

```json
      "costs": {
        "title": "Costes de red",
        "description": "{model}. Sigue lo que cuesta la energía que compras a la red y la que le vendes. Cada sentido tiene su precio: fijo, o leído de una entidad de Home Assistant.",
        "data": {
          "enabled": "Seguimiento de costes",
          "import_mode": "Precio de la importada",
          "export_mode": "Precio de la exportada"
        },
        "submit": "Siguiente"
      },
      "cost_prices": {
        "title": "Precios",
        "description": "Los precios fijos van en €/kWh. Una entidad de precio debe estar en €/kWh o €/MWh.",
        "data": {
          "import_price": "Precio de la importada",
          "export_price": "Precio de la exportada",
          "import_entity": "Entidad del precio de la importada",
          "export_entity": "Entidad del precio de la exportada"
        },
        "submit": "Siguiente"
      },
```

En `config.error`: `"price_unit_invalid": "La entidad debe tener unidad €/kWh o €/MWh."`.
En `selector`: `"cost_mode": { "options": { "fixed": "Precio fijo", "dynamic": "Precio dinámico (entidad)" } }`.

Antes de copiar, comprobar con `grep -n '"submit"' custom_components/modbus_solar/strings.json` el texto del botón de
los pasos vecinos y usar el mismo.

- [ ] **Step 5: Lint y commit del verde**

Run: `bash scripts/lint.sh`

```bash
git add custom_components/modbus_solar/adapters/inbound/flow.py custom_components/modbus_solar/strings.json custom_components/modbus_solar/translations/en.json custom_components/modbus_solar/translations/es.json
git commit -m "feat: pasos de costes de red en el alta"
```

Con push, expected: CI en verde (incluido hassfest, que valida `strings.json`).

---

### Task 6: Costes en reconfigurar y en la lista de entidades

**Files:**
- Modify: `adapters/inbound/flow.py` (`entity_list`, `async_step_reconfigure_metering`,
  `async_step_reconfigure_intervals`, pasos nuevos), `strings.json`, `translations/*.json`
- Test: `tests/ha/test_config_flow.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: todo lo de la Task 5 (`has_costs`, `_show_costs`, `_show_cost_prices`, `price_errors`, `costs_data`,
  `_costs`, `_cost_modes`, `COST_DIRECTIONS`, `CONF_ENABLED`).
- Produces: `_after_reconfigure_metering()`, pasos `async_step_reconfigure_costs` y
  `async_step_reconfigure_cost_prices`.

- [ ] **Step 1: Tests que fallan**

`tests/ha/test_config_flow.py`, tests existentes de reconfigurar: tras el `configure` de `metering` de las líneas
605, 641, 703, 717 y 863 (modos `grid_loads` y `critical_loads`), insertar:

```python
    result = await configure(hass, result, {"enabled": False})
```

En 605 y 717, que comprueban el paso siguiente, el assert de `reconfigure_components` queda tras esa línea. En 605,
añadir antes `assert result["step_id"] == "reconfigure_costs"`.

Tests nuevos tras `test_reconfigure_four_steps`:

```python
async def test_reconfigure_costs_start_from_saved(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry(costs=FIXED_COSTS)
    result = await reconfigure(hass, entry)
    result = await configure(hass, result, {"metering": "grid_loads"})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_costs")
    assert field(result, "enabled").default() is True
    result = await configure(hass, result, {"enabled": True, "import_mode": "fixed", "export_mode": "fixed"})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_cost_prices")
    assert field(result, "import_price").description == {"suggested_value": 0.15}
    result = await configure(hass, result, {"import_price": 0.2, "export_price": 0.05})
    assert result["step_id"] == "reconfigure_components"
    result = await configure(hass, result, {"components": ["grid", "battery"]})
    result = await configure(hass, result, STORAGE_INTERVALS)
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["costs"] == {"import": {"mode": "fixed", "price": 0.2}, "export": {"mode": "fixed", "price": 0.05}}


async def test_reconfigure_disabling_costs_drops_the_key(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry(costs=FIXED_COSTS)
    result = await reconfigure(hass, entry)
    result = await configure(hass, result, {"metering": "grid_loads"})
    result = await configure(hass, result, {"enabled": False})
    result = await configure(hass, result, {"components": ["grid", "battery"]})
    result = await configure(hass, result, STORAGE_INTERVALS)
    assert result["reason"] == "reconfigure_successful"
    assert "costs" not in entry.data


async def test_reconfigure_off_grid_drops_costs(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry(costs=FIXED_COSTS)
    result = await reconfigure(hass, entry)
    result = await configure(hass, result, {"metering": "off_grid"})
    assert result["step_id"] == "reconfigure_components"
    result = await configure(hass, result, {"components": ["battery", "internal_meter"]})
    result = await configure(hass, result, {k: v for k, v in STORAGE_INTERVALS.items() if k != "instant"})
    assert result["reason"] == "reconfigure_successful"
    assert "costs" not in entry.data


async def test_intervals_list_cost_sensors(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_costs(hass)
    result = await configure(hass, result, {"enabled": True, "import_mode": "fixed", "export_mode": "fixed"})
    result = await configure(hass, result, {"import_price": 0.15, "export_price": 0.05})
    result = await configure(hass, result, {"components": ["grid", "battery"]})
    result = await choose(hass, result, "name")
    result = await configure(hass, result, {"name": "House", "device_id": 0})
    assert result["step_id"] == "intervals"
    assert "- Grid · Grid import cost" in result["description_placeholders"]["instant_entities"]
    assert "- Grid · Grid export cost" in result["description_placeholders"]["instant_entities"]
```

Si `test_reconfigure_off_grid_drops_costs` falla en los intervalos (tiers distintos de los esperados), leer la salida
del CI y ajustar solo el diccionario de intervalos a las secciones que muestre el formulario.

`tests/unit/test_translations.py`, en `test_flow_steps_errors_and_aborts_are_translated`: añadir
`"reconfigure_costs"` y `"reconfigure_cost_prices"`. En `test_cost_steps_and_modes_are_translated`, comprobar
también que `steps["reconfigure_costs"]["data"] == steps["costs"]["data"]` y
`steps["reconfigure_cost_prices"]["data"] == steps["cost_prices"]["data"]`.

- [ ] **Step 2: Lint y commit del rojo**

Run: `bash scripts/lint.sh`

```bash
git add tests/ha/test_config_flow.py tests/unit/test_translations.py
git commit -m "test(red): costes en reconfigurar y en la lista de entidades"
```

Con push, expected: rojo en los tests nuevos y en los cinco de reconfigurar tocados (el paso siguiente aún es
`reconfigure_components`).

- [ ] **Step 3: Implementación**

`entity_list`: los costes van en «calculated», tras las energías:

```python
    costs = sorted((c for c in selection.costs if poll_of[c.source] is tier), key=lambda c: order.index(c.component))
    ...
    if powers or energies or costs:
        lines = [line(p.component, "sensor", p.key, p.enabled_default) for p in powers]
        lines += [line(e.component, "sensor", e.key, e.enabled_default) for e in energies]
        lines += [line(c.component, "sensor", c.key, c.enabled_default) for c in costs]
        parts.append("\n".join([calculated, *lines]))
```

Y su docstring pasa a «leídas, potencias, energías y costes calculados y controles».

Reconfigurar:

```python
    async def async_step_reconfigure_metering(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        profile = self._profile
        if user_input is not None:
            self._metering = user_input[CONF_METERING]
            if has_costs(profile, self._metering):
                return await self.async_step_reconfigure_costs()
            self._costs = None
            return await self._after_reconfigure_metering()
        # sin modo guardado (entry anterior), el primero del perfil
        return self._show_metering("reconfigure_metering", profile, entry.data.get(CONF_METERING))

    async def _after_reconfigure_metering(self) -> ConfigFlowResult:
        if self._profile.components:
            return await self.async_step_reconfigure_components()
        self._components = []
        return await self.async_step_reconfigure_intervals()

    async def async_step_reconfigure_costs(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            if not user_input[CONF_ENABLED]:
                self._costs = None
                return await self._after_reconfigure_metering()
            self._cost_modes = {d: user_input[f"{d}_mode"] for d in COST_DIRECTIONS}
            return await self.async_step_reconfigure_cost_prices()
        return self._show_costs("reconfigure_costs", entry.data.get(CONF_COSTS))

    async def async_step_reconfigure_cost_prices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = price_errors(self.hass, self._cost_modes, user_input)
            if not errors:
                self._costs = costs_data(self._cost_modes, user_input)
                return await self._after_reconfigure_metering()
        return self._show_cost_prices("reconfigure_cost_prices", entry.data.get(CONF_COSTS), errors, user_input)
```

`async_step_reconfigure_intervals`: `tiers = present_tiers(select(profile, components, self._metering, self._costs))`
y, en el bucle que pone o quita `CONF_DEVICE_ID` y `CONF_SERIAL_NUMBER`, añadir `(CONF_COSTS, self._costs)` a la
tupla: sin seguimiento, la clave desaparece.

Un perfil sin modos de medición (1Play) no pasa por `reconfigure_metering`: `self._costs` queda en `None` y el `pop`
no encuentra la clave. Es lo correcto: esos perfiles no tienen costes.

- [ ] **Step 4: Traducciones**

En `strings.json`, `translations/en.json` y `translations/es.json`: `reconfigure_costs` y
`reconfigure_cost_prices` con el mismo `title`, `data` y `submit` que `costs` y `cost_prices`. Descripción de
`reconfigure_costs`:

- en: `"{model}. Unticking it removes both cost sensors with their history."`
- es: `"{model}. Si desmarcas la casilla, se borran los dos sensores de coste con su historial."`

`reconfigure_cost_prices` usa la misma descripción que `cost_prices`.

- [ ] **Step 5: Lint y commit del verde**

Run: `bash scripts/lint.sh`

```bash
git add custom_components/modbus_solar/adapters/inbound/flow.py custom_components/modbus_solar/strings.json custom_components/modbus_solar/translations/en.json custom_components/modbus_solar/translations/es.json
git commit -m "feat: costes de red en reconfigurar"
```

Con push, expected: CI en verde (lint, test, hacs y hassfest).

---

### Task 7: Docs vivas, CHANGELOG y cierre de la spec

**Files:**
- Modify: `docs/features/device-setup.md`, `docs/features/monitoring.md`, `docs/architecture/domain.md`,
  `docs/architecture/application.md`, `docs/architecture/adapters/inbound.md`, `CHANGELOG.md`,
  `docs/changes/2026-10-11-grid-costs/spec.md`, `docs/changes/2026-10-11-grid-costs/plan.md`

- [ ] **Step 1: Invocar la skill `project-docs` en modo sync** sobre la spec. Debe:
  - describir en `device-setup.md` los pasos «Costes de red» y «Precios», en el alta y en reconfigurar;
  - añadir en `monitoring.md` los dos sensores de coste: unidad, dispositivo, precio caído y restauración;
  - añadir `domain/cost.py`, `FlowSpec.cost_key/cost_role` y `DerivedCostSpec` a `architecture/domain.md`;
  - añadir `Selection.costs` y `select(..., costs)` a `architecture/application.md`;
  - añadir `entities/cost.py`, `DeviceRuntime.costs` y los pasos del flujo a `architecture/adapters/inbound.md`;
  - abrir en `CHANGELOG.md` una sección `## [Unreleased]` con «Seguimiento de costes de red en el STORAGE 1Play TL
    M: precio fijo o dinámico por sentido y sensores de coste de la energía importada y exportada.»;
  - poner `status: done` en la spec y en el plan, y comprobar que la spec no tiene líneas sueltas.
  Cada afirmación nueva de las docs cita `archivo:línea` del código ya implementado.

- [ ] **Step 2: Commit**

```bash
git add docs CHANGELOG.md
git commit -m "docs: costes de red"
```

Con push, expected: CI en verde.
