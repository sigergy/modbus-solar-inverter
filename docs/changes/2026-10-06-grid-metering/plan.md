---
type: feature
area: energy
layers: [domain, application, adapters, profiles]
status: done
date: 2026-10-06
---

# Plan de implementación — Medición de red en el STORAGE 1Play TL M

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `subagent-driven-development` (recomendada) o `executing-plans`
> para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** implementar la [spec](spec.md). Desplegable «Medición de red» con tres modos. Potencias derivadas
importada, exportada y del generador. Energías de red calculadas desde la fuente del modo. Dispositivo Generador.

**Arquitectura:** hexagonal, vigilada por import-linter. El dominio gana `domain/metering.py`, `filter_power` y la
validación. `application/selection.py` resuelve el modo: componentes forzados, potencias y energías del modo. Los
adaptadores crean el sensor derivado, limpian el registro y añaden los pasos del flujo. `domain`, `ports`,
`application` y `profiles` no importan HA.

**Stack:** Python 3.14, Home Assistant 2026.9.4, pytest con `pytest-homeassistant-custom-component` (solo en CI),
ruff (línea de 120), import-linter, hassfest y HACS en `validate.yml`.

Rutas de código relativas a `custom_components/modbus_solar/` salvo indicación.

## Global Constraints

- Rama `feat/grid-metering` con base `docs/grid-metering` (contiene spec y plan). Sin worktree. Push autorizado a esa
  rama con `bash scripts/ci-wait.sh`. Force push, merge, rebase y PR piden confirmación.
- Tests solo en CI: nunca `pytest` en local. El gate local es `bash scripts/lint.sh` antes de cada commit.
- Cada tarea: commit `test(red): …` con los tests que fallan (CI en rojo por esos tests y solo esos). Después,
  commit `feat: …` (o `refactor: …`, `docs: …`) con CI en verde. Si un test(red) no puede ni importar (símbolo
  nuevo), el rojo es el error de import de ese fichero: vale.
- Trailer obligatorio en cada commit:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01LnEE7K8DMBv1fGShyVtvti
  ```
- Comentarios en español; identificadores, ficheros y tests en inglés. Dentro del paquete, solo imports relativos.
- Antes de orientarse, `graft ask "<pregunta>" --source` o `graft grep "<símbolo>"`; antes de cambiar una firma,
  `graft callers <símbolo> --depth 2`. `graft/` y `.graft_*` no se commitean nunca.
- `VERSION` del flujo sigue en 2; sin `async_migrate_entry` (spec §8). Los `unique_id` de `grid_import_energy` y
  `grid_export_energy` no cambian.
- `en.json` es copia literal de `strings.json`; `es.json` tiene las mismas claves (`tests/unit/test_translations.py`).
- No inventar: si una API (de HA o del código) no se comporta como dice el plan, parar y avisar con la salida real.
  Las citas `archivo:línea` son de `3142b60`; tras cada tarea pueden moverse.

## Mapa de ficheros

| Fichero | Cambio | Tarea |
|---|---|---|
| `domain/types.py` | `Component.GENERATOR`; 4 roles | 1 |
| `domain/energy.py` | `filter_power`; `EnergyAccumulator` la usa | 1 |
| `domain/metering.py` | nuevo: `FlowSpec`, `MeteringModeSpec`, `DerivedPowerSpec` | 1 |
| `domain/profile.py` | `DeviceProfile.metering_modes` | 1 |
| `domain/validate.py` | `_metering_problems` | 2 |
| `application/selection.py` | `metering_mode`, `required_component`, `select(..., metering)`, `Selection.powers` | 3 |
| `profiles/ingeteam/oneplay_storage.py` | tres modos; las energías de red salen de `energies` | 4 |
| `adapters/inbound/entities/derived.py` | nuevo: `ModbusSolarDerivedPowerSensor` | 5 |
| `adapters/inbound/entities/factory.py`, `base.py` | crear potencias; tipo del spec | 5 |
| `adapters/inbound/runtime.py` | `enabled_keys` con las fuentes de las potencias | 5 |
| `const.py` | `CONF_METERING` | 5 |
| `__init__.py` | `select` con el modo (5); `_remove_unselected` con modos (6) | 5, 6 |
| `adapters/inbound/flow.py` | paso `metering`, componente forzado, `entity_list` (7); `reconfigure_metering` (8) | 7, 8 |
| `strings.json`, `translations/en.json`, `translations/es.json` | dispositivo (1), entidades (4), alta (7), reconfigurar (8) | 1, 4, 7, 8 |
| `tests/unit/*`, `tests/ha/*` | ver cada tarea | 1-8 |
| `docs/…`, `CHANGELOG.md`, ADR 0017 | sync | 9 |

---

### Tarea 0: rama

La crea el orquestador antes de la Tarea 1:

```bash
git switch -c feat/grid-metering docs/grid-metering
git push -u origin feat/grid-metering
```

---

### Tarea 1: tipos de dominio, `filter_power` y `domain/metering.py`

**Files:**
- Create: `domain/metering.py`
- Modify: `domain/types.py` (`Role`, `Component`), `domain/energy.py:41-44`, `domain/profile.py:76-91`
- Modify: `strings.json`, `translations/en.json`, `translations/es.json` (sección `device`)
- Test: `tests/unit/test_energy.py`, `tests/unit/test_types.py`

**Interfaces:**
- Produces:
  - `filter_power(power_w: float, sign: SignFilter) -> float` en `domain/energy.py`.
  - `Component.GENERATOR = "generator"` (último miembro).
  - `Role.GRID_IMPORT_POWER = "grid_import_power"`, `Role.GRID_EXPORT_POWER = "grid_export_power"`,
    `Role.GENERATOR_POWER = "generator_power"`, `Role.ENERGY_GENERATOR = "energy_generator"` (al final, en ese orden).
  - `domain/metering.py`: `FlowSpec`, `MeteringModeSpec`, `DerivedPowerSpec` (código abajo).
  - `DeviceProfile.metering_modes: tuple[MeteringModeSpec, ...] = ()`.

- [ ] **Step 1: tests que fallan**

`tests/unit/test_energy.py`: importar `filter_power` junto a lo que ya importa y añadir:

```python
def test_filter_power() -> None:
    assert filter_power(1500.0, SignFilter.POSITIVE) == 1500.0
    assert filter_power(-1500.0, SignFilter.POSITIVE) == 0.0
    assert filter_power(-1500.0, SignFilter.NEGATIVE) == 1500.0
    assert filter_power(1500.0, SignFilter.NEGATIVE) == 0.0
```

`tests/unit/test_types.py`, en `test_enum_values_are_stable`:
- lista de `Component`: añadir `"generator"` al final, tras `"ev_charger"`;
- lista de `Role`: añadir al final, tras `"external_temperature"`:
  `"grid_import_power"`, `"grid_export_power"`, `"generator_power"`, `"energy_generator"`.

Y añadir al final del fichero:

```python
def test_metering_specs_are_frozen_and_profile_has_no_modes_by_default() -> None:
    flow = FlowSpec(
        power_key="grid_import_power",
        power_role=Role.GRID_IMPORT_POWER,
        energy_key="grid_import_energy",
        energy_role=Role.ENERGY_GRID_IMPORT,
        sign=SignFilter.POSITIVE,
    )
    mode = MeteringModeSpec(key="grid_loads", source="grid_power", component=Component.GRID, flows=(flow,))
    power = DerivedPowerSpec(
        key="grid_import_power",
        role=Role.GRID_IMPORT_POWER,
        source="grid_power",
        sign=SignFilter.POSITIVE,
        component=Component.GRID,
    )
    assert power.enabled_default is True
    for spec in (flow, mode, power):
        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.key = "x"  # type: ignore[misc]
    profile = DeviceProfile(
        id="t.d",
        brand="t",
        device_type="inverter",
        models=("M",),
        min_request_interval_s=1.0,
        default_port=502,
        default_unit_id=1,
        probe_key="a",
        entities=(),
    )
    assert profile.metering_modes == ()
```

Un dataclass `frozen` lanza `FrozenInstanceError` al asignar cualquier atributo, también `key` en `FlowSpec` (que no
lo tiene). Imports del test: `from custom_components.modbus_solar.domain.energy import SignFilter` y
`from custom_components.modbus_solar.domain.metering import DerivedPowerSpec, FlowSpec, MeteringModeSpec`.

- [ ] **Step 2:** `bash scripts/lint.sh`; commit `test(red): metering domain types and filter_power`;
  `bash scripts/ci-wait.sh` → rojo en `test_energy.py` y `test_types.py`.

- [ ] **Step 3: implementación**

`domain/energy.py`: añadir tras `SignFilter` y usarla en `EnergyAccumulator.add`:

```python
def filter_power(power_w: float, sign: SignFilter) -> float:
    """Parte de la potencia que cuenta según el signo: la positiva, o la negativa en valor absoluto."""
    return max(power_w, 0.0) if sign is SignFilter.POSITIVE else max(-power_w, 0.0)
```

```python
        filtered = filter_power(power_w, self._sign)
```

`domain/types.py`: los 4 roles al final de `Role` (comentario: `# potencias derivadas y energía del generador
(medición de red)`) y `GENERATOR = "generator"` al final de `Component`.

`domain/metering.py`:

```python
"""Medición de red: el modo elige la potencia leída que mide el intercambio y el dispositivo de sus entidades."""

from dataclasses import dataclass

from .energy import SignFilter
from .types import Component, Role


@dataclass(frozen=True, kw_only=True)
class FlowSpec:
    """Un sentido del intercambio: su potencia derivada y la energía que la integra."""

    power_key: str
    power_role: Role
    energy_key: str
    energy_role: Role
    sign: SignFilter


@dataclass(frozen=True, kw_only=True)
class MeteringModeSpec:
    key: str  # valor guardado en la entry y clave de traducción
    source: str  # clave de la entidad de potencia leída (W)
    component: Component  # dispositivo de las entidades del modo
    flows: tuple[FlowSpec, ...]


@dataclass(frozen=True, kw_only=True)
class DerivedPowerSpec:
    """Potencia calculada: la fuente leída filtrada por signo."""

    key: str  # también translation_key y sufijo del unique_id
    role: Role
    source: str
    sign: SignFilter
    component: Component
    enabled_default: bool = True
```

`domain/profile.py`: importar `MeteringModeSpec` y añadir al final de `DeviceProfile`:

```python
    # modos de medición de red; el primero es el de por defecto
    metering_modes: tuple[MeteringModeSpec, ...] = ()
```

Traducciones, sección `device` (la exige `test_device_names_have_no_device_id`, que recorre todo `Component`):
`strings.json` y `en.json` → `"generator": {"name": "Generator"}`; `es.json` → `"generator": {"name": "Generador"}`.

- [ ] **Step 4:** lint; commit `feat: metering domain types and shared sign filter`; ci-wait → verde.

---

### Tarea 2: validación de los modos

**Files:**
- Modify: `domain/validate.py`
- Test: `tests/unit/test_validate.py`

**Interfaces:**
- Consumes: `FlowSpec`, `MeteringModeSpec` (Tarea 1); helpers `ent`, `power`, `profile` de `test_validate.py`.
- Produces: mensajes exactos `metering: {key} repeated`, `metering {key}: no flows`,
  `metering {key}: unknown source {source}`, `metering {key}: source {source} is not power`,
  `duplicate key: {key}`, `metering: {key} differs between modes`.

- [ ] **Step 1: tests que fallan** — al final de `tests/unit/test_validate.py` (importar `FlowSpec`,
  `MeteringModeSpec`):

```python
def flow(power_key: str = "p_in", energy_key: str = "e_in", sign: SignFilter = SignFilter.POSITIVE) -> FlowSpec:
    return FlowSpec(
        power_key=power_key,
        power_role=Role.GRID_IMPORT_POWER,
        energy_key=energy_key,
        energy_role=Role.ENERGY_GRID_IMPORT,
        sign=sign,
    )


def mode(key: str = "m", source: str = "a", flows: tuple[FlowSpec, ...] | None = None) -> MeteringModeSpec:
    return MeteringModeSpec(
        key=key, source=source, component=Component.GENERATOR, flows=(flow(),) if flows is None else flows
    )


def with_modes(*modes: MeteringModeSpec, entities: tuple[EntitySpec, ...] = ()) -> DeviceProfile:
    return replace(profile(*(entities or (power("a", 0), ent("b", 1)))), metering_modes=modes)


def test_metering_valid() -> None:
    # dos modos comparten claves con el mismo rol y signo; Generador no está declarado y vale
    assert validate_profile(with_modes(mode("x"), mode("y"))) == []


def test_metering_mode_repeated_or_without_flows() -> None:
    assert validate_profile(with_modes(mode("x"), mode("x"))) == ["metering: x repeated"]
    assert validate_profile(with_modes(mode("x", flows=()))) == ["metering x: no flows"]


def test_metering_source_must_be_known_power() -> None:
    assert validate_profile(with_modes(mode("x", source="z"))) == ["metering x: unknown source z"]
    assert validate_profile(with_modes(mode("x", source="b"))) == ["metering x: source b is not power"]


def test_metering_keys_do_not_clash() -> None:
    # con una entidad, consigo mismas dentro del modo
    assert validate_profile(with_modes(mode("x", flows=(flow(power_key="b"),)))) == ["duplicate key: b"]
    assert validate_profile(with_modes(mode("x", flows=(flow(), flow())))) == [
        "duplicate key: p_in",
        "duplicate key: e_in",
    ]


def test_metering_key_same_role_and_sign_across_modes() -> None:
    other = mode("y", flows=(flow(sign=SignFilter.NEGATIVE),))
    assert validate_profile(with_modes(mode("x"), other)) == [
        "metering: p_in differs between modes",
        "metering: e_in differs between modes",
    ]
```

Comprobar con `ent` que la entidad `b` no tiene `device_class` (por eso «is not power»).

- [ ] **Step 2:** lint; commit `test(red): metering mode validation`; ci-wait → rojo.

- [ ] **Step 3: implementación** — en `domain/validate.py` (importar `SignFilter` y `Role`):

```python
def _metering_problems(profile: DeviceProfile, seen: set[str]) -> list[str]:
    """Modos de medición: clave única, fuente de potencia leída y claves de flujo sin choques."""
    problems: list[str] = []
    by_key = {spec.key: spec for spec in profile.entities}
    modes: set[str] = set()
    # una clave puede repetirse entre modos (mismo unique_id): con el mismo rol y signo
    flow_keys: dict[str, tuple[Role, SignFilter]] = {}
    for mode in profile.metering_modes:
        if mode.key in modes:
            problems.append(f"metering: {mode.key} repeated")
        modes.add(mode.key)
        if not mode.flows:
            problems.append(f"metering {mode.key}: no flows")
        source = by_key.get(mode.source)
        if source is None:
            problems.append(f"metering {mode.key}: unknown source {mode.source}")
        elif source.device_class != "power":
            problems.append(f"metering {mode.key}: source {mode.source} is not power")
        mode_keys: set[str] = set()
        for flow in mode.flows:
            for key, role in ((flow.power_key, flow.power_role), (flow.energy_key, flow.energy_role)):
                if key in seen or key in mode_keys:
                    problems.append(f"duplicate key: {key}")
                mode_keys.add(key)
                if flow_keys.setdefault(key, (role, flow.sign)) != (role, flow.sign):
                    problems.append(f"metering: {key} differs between modes")
    return problems
```

Llamarla en `validate_profile` justo después del bucle de controles y antes de `_component_problems`:
`problems.extend(_metering_problems(profile, seen))`. El componente de la fuente ya lo valida
`_component_problems` (la fuente es una entidad del perfil); `mode.component` no se valida (spec §5.4).

- [ ] **Step 4:** lint; commit `feat: validate metering modes`; ci-wait → verde.

---

### Tarea 3: selección por modo

**Files:**
- Modify: `application/selection.py`
- Test: `tests/unit/test_selection.py`

**Interfaces:**
- Consumes: Tarea 1.
- Produces:
  - `Selection.powers: tuple[DerivedPowerSpec, ...] = ()` (último campo, con valor por defecto).
  - `metering_mode(profile: DeviceProfile, metering: str | None) -> MeteringModeSpec | None`.
  - `required_component(profile: DeviceProfile, mode: MeteringModeSpec) -> Component`.
  - `chosen_components(profile, components, metering: str | None = None) -> set[Component]`.
  - `select(profile, components, metering: str | None = None) -> Selection`.

- [ ] **Step 1: tests que fallan** — en `tests/unit/test_selection.py` (importar `FlowSpec`, `MeteringModeSpec`,
  `SignFilter`, `Role`, `chosen_components`, `metering_mode`, `required_component`, y `power` de `test_validate`):

```python
def metered():
    entities = (
        ent("a", 0),
        replace(power("g", 1), component=Component.GRID),
        replace(power("m", 2), component=Component.INTERNAL_METER),
    )
    grid = (
        FlowSpec(
            power_key="in_p",
            power_role=Role.GRID_IMPORT_POWER,
            energy_key="in_e",
            energy_role=Role.ENERGY_GRID_IMPORT,
            sign=SignFilter.POSITIVE,
        ),
        FlowSpec(
            power_key="out_p",
            power_role=Role.GRID_EXPORT_POWER,
            energy_key="out_e",
            energy_role=Role.ENERGY_GRID_EXPORT,
            sign=SignFilter.NEGATIVE,
        ),
    )
    generator = FlowSpec(
        power_key="gen_p",
        power_role=Role.GENERATOR_POWER,
        energy_key="gen_e",
        energy_role=Role.ENERGY_GENERATOR,
        sign=SignFilter.POSITIVE,
    )
    modes = (
        MeteringModeSpec(key="external", source="g", component=Component.GRID, flows=grid),
        MeteringModeSpec(key="internal", source="m", component=Component.INTERNAL_METER, flows=grid),
        MeteringModeSpec(key="island", source="m", component=Component.GENERATOR, flows=(generator,)),
    )
    components = (ComponentSpec(Component.GRID), ComponentSpec(Component.INTERNAL_METER, default=False))
    return replace(profile(*entities), components=components, metering_modes=modes)


def test_metering_mode_defaults_to_first() -> None:
    assert metering_mode(metered(), None).key == "external"
    assert metering_mode(metered(), "unknown").key == "external"
    assert metering_mode(metered(), "island").key == "island"
    assert metering_mode(two_components(), None) is None


def test_required_component_is_the_source_component() -> None:
    profile_ = metered()
    assert required_component(profile_, metering_mode(profile_, "island")) is Component.INTERNAL_METER


def test_mode_forces_meter_and_device() -> None:
    assert chosen_components(metered(), [], "internal") == {Component.MAIN, Component.INTERNAL_METER}
    assert chosen_components(metered(), [], "island") == {
        Component.MAIN,
        Component.INTERNAL_METER,
        Component.GENERATOR,
    }
    # sin modo, nada cambia
    assert chosen_components(two_components(), []) == {Component.MAIN}


def test_select_adds_powers_and_energies_of_the_mode() -> None:
    selection = select(metered(), [], None)
    assert [e.key for e in selection.entities] == ["a", "g"]
    assert [(p.key, p.source, p.sign, p.component) for p in selection.powers] == [
        ("in_p", "g", SignFilter.POSITIVE, Component.GRID),
        ("out_p", "g", SignFilter.NEGATIVE, Component.GRID),
    ]
    assert [(e.key, e.sources, e.sign, e.component) for e in selection.energies] == [
        ("in_e", ("g",), SignFilter.POSITIVE, Component.GRID),
        ("out_e", ("g",), SignFilter.NEGATIVE, Component.GRID),
    ]


def test_select_internal_and_island() -> None:
    internal = select(metered(), [Component.GRID], "internal")
    assert [e.key for e in internal.entities] == ["a", "g", "m"]
    assert {(p.source, p.component) for p in internal.powers} == {("m", Component.INTERNAL_METER)}
    island = select(metered(), [], "island")
    assert [(p.key, p.component) for p in island.powers] == [("gen_p", Component.GENERATOR)]
    assert [(e.key, e.sources) for e in island.energies] == [("gen_e", ("m",))]


def test_profile_without_modes_has_no_powers() -> None:
    assert select(two_components(), None).powers == ()
```

- [ ] **Step 2:** lint; commit `test(red): selection by metering mode`; ci-wait → rojo.

- [ ] **Step 3: implementación** — `application/selection.py`:

```python
@dataclass(frozen=True)
class Selection:
    entities: tuple[EntitySpec, ...]
    energies: tuple[EnergySpec, ...]
    controls: tuple[GatedLimitSpec, ...]
    powers: tuple[DerivedPowerSpec, ...] = ()  # potencias derivadas del modo de medición


def metering_mode(profile: DeviceProfile, metering: str | None) -> MeteringModeSpec | None:
    """Modo guardado. None (entry sin modo) o clave desconocida = el primero. None si el perfil no tiene modos."""
    if not profile.metering_modes:
        return None
    return next((m for m in profile.metering_modes if m.key == metering), profile.metering_modes[0])


def required_component(profile: DeviceProfile, mode: MeteringModeSpec) -> Component:
    """Componente del vatímetro del modo: el de su entidad fuente."""
    return next(e.component for e in profile.entities if e.key == mode.source)


def chosen_components(
    profile: DeviceProfile, components: Collection[Component] | None, metering: str | None = None
) -> set[Component]:
    """Componentes elegidos más el principal. None = entry anterior a v2: todos los opcionales.

    El modo de medición añade su vatímetro y el dispositivo de sus entidades.
    """
    chosen = {c.component for c in profile.components} if components is None else set(components)
    chosen.add(Component.MAIN)
    mode = metering_mode(profile, metering)
    if mode is not None:
        chosen |= {required_component(profile, mode), mode.component}
    return chosen


def select(
    profile: DeviceProfile, components: Collection[Component] | None, metering: str | None = None
) -> Selection:
    chosen = chosen_components(profile, components, metering)
    mode = metering_mode(profile, metering)
    powers: tuple[DerivedPowerSpec, ...] = ()
    mode_energies: tuple[EnergySpec, ...] = ()
    if mode is not None:
        powers = tuple(
            DerivedPowerSpec(
                key=f.power_key, role=f.power_role, source=mode.source, sign=f.sign, component=mode.component
            )
            for f in mode.flows
        )
        # la energía integra la fuente con el signo del flujo: el mismo número que integrar la potencia derivada
        mode_energies = tuple(
            EnergySpec(
                key=f.energy_key, role=f.energy_role, sources=(mode.source,), sign=f.sign, component=mode.component
            )
            for f in mode.flows
        )
    return Selection(
        entities=tuple(e for e in profile.entities if e.component in chosen),
        energies=tuple(e for e in profile.energies if e.component in chosen) + mode_energies,
        controls=tuple(c for c in profile.controls if c.component in chosen),
        powers=powers,
    )
```

Efecto conocido: una entry STORAGE sin `metering` y sin `grid` en `components` gana el componente Red (spec §8: sin
modo guardado = «Consumos en Grid»). Los tests HA actuales con `components=["battery"]` no comprueban la ausencia de
Red; si alguno falla por eso en CI, parar y avisar.

- [ ] **Step 4:** lint; commit `feat: select entities by metering mode`; ci-wait → verde.

---

### Tarea 4: modos del perfil STORAGE y nombres de las entidades

**Files:**
- Modify: `profiles/ingeteam/oneplay_storage.py:400-439` (quitar las dos energías de red; añadir `metering_modes`)
- Modify: `strings.json`, `translations/en.json`, `translations/es.json` (`entity.sensor`)
- Test: `tests/unit/test_storage_profile.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: Tareas 1-3.
- Produces: modos `grid_loads`, `critical_loads`, `off_grid` (spec §4) con claves `grid_import_power`,
  `grid_export_power`, `grid_import_energy`, `grid_export_energy`, `generator_power`, `generator_energy`.

- [ ] **Step 1: tests que fallan**

`tests/unit/test_storage_profile.py`:
- `test_energies`: quitar las dos tuplas de `grid_import_energy` y `grid_export_energy` (quedan solar y batería).
- `test_entities_per_component`: `Component.GRID: 5` pasa a `Component.GRID: 3`.
- Añadir (importar `select` de `application.selection`):

```python
def test_metering_modes() -> None:
    # spec §4; signos supuestos: 30072 y 30052 > 0 = entra potencia por las bornas de red
    grid = [
        ("grid_import_power", Role.GRID_IMPORT_POWER, "grid_import_energy", Role.ENERGY_GRID_IMPORT, SignFilter.POSITIVE),
        ("grid_export_power", Role.GRID_EXPORT_POWER, "grid_export_energy", Role.ENERGY_GRID_EXPORT, SignFilter.NEGATIVE),
    ]
    generator = [
        ("generator_power", Role.GENERATOR_POWER, "generator_energy", Role.ENERGY_GENERATOR, SignFilter.POSITIVE)
    ]
    modes = [
        (m.key, m.source, m.component, [(f.power_key, f.power_role, f.energy_key, f.energy_role, f.sign) for f in m.flows])
        for m in PROFILE.metering_modes
    ]
    assert modes == [
        ("grid_loads", "grid_power", Component.GRID, grid),
        ("critical_loads", "internal_meter_power", Component.INTERNAL_METER, grid),
        ("off_grid", "internal_meter_power", Component.GENERATOR, generator),
    ]


def test_default_mode_keeps_grid_energies_on_grid() -> None:
    selection = select(PROFILE, None)
    energies = {e.key: (e.sources, e.component) for e in selection.energies}
    assert energies["grid_import_energy"] == (("grid_power",), Component.GRID)
    assert energies["grid_export_energy"] == (("grid_power",), Component.GRID)
    assert [p.key for p in selection.powers] == ["grid_import_power", "grid_export_power"]
```

(Si alguna línea pasa de 120 columnas, `ruff format` la parte; no cambia el contenido.)

`tests/unit/test_translations.py`:
- en `test_every_entity_and_enum_state_is_translated`, dentro del bucle de perfiles, tras el de energías:

```python
        for mode in profile.metering_modes:
            for flow in mode.flows:
                assert "name" in entities["sensor"][flow.power_key], flow.power_key
                assert "name" in entities["sensor"][flow.energy_key], flow.energy_key
```

- añadir:

```python
def test_metering_entity_names() -> None:
    expected = {
        "strings.json": {
            "grid_import_power": "Grid import power",
            "grid_export_power": "Grid export power",
            "generator_power": "Generator power",
            "generator_energy": "Generator energy",
        },
        "translations/es.json": {
            "grid_import_power": "Potencia de red",
            "grid_export_power": "Potencia a la red",
            "generator_power": "Potencia del generador",
            "generator_energy": "Energía del generador",
        },
    }
    for name, names in expected.items():
        sensors = load(name)["entity"]["sensor"]
        assert {key: sensors[key]["name"] for key in names} == names, name
```

- [ ] **Step 2:** lint; commit `test(red): storage metering modes`; ci-wait → rojo.

- [ ] **Step 3: implementación**

`profiles/ingeteam/oneplay_storage.py`: importar `FlowSpec`, `MeteringModeSpec` de `...domain.metering`. Quitar de
`energies` los `EnergySpec` de `grid_import_energy` y `grid_export_energy`; ajustar el comentario de encima (los
signos de red ahora los llevan los modos). Añadir antes de `ONEPLAY_STORAGE`:

```python
# intercambio con la red: mismas claves (y unique_id) con el vatímetro externo o con el interno
GRID_FLOWS = (
    FlowSpec(
        power_key="grid_import_power",
        power_role=Role.GRID_IMPORT_POWER,
        energy_key="grid_import_energy",
        energy_role=Role.ENERGY_GRID_IMPORT,
        sign=SignFilter.POSITIVE,
    ),
    FlowSpec(
        power_key="grid_export_power",
        power_role=Role.GRID_EXPORT_POWER,
        energy_key="grid_export_energy",
        energy_role=Role.ENERGY_GRID_EXPORT,
        sign=SignFilter.NEGATIVE,
    ),
)
```

Y en `ONEPLAY_STORAGE`, tras `energies`:

```python
    # spec grid-metering §4. Signos supuestos (sin verificar en el equipo): 30072 y 30052 > 0 = entra potencia
    # por las bornas de red. En aislada las bornas de red llevan el grupo electrógeno (ABH2014IQM01, apdo. 11, pág. 32)
    metering_modes=(
        MeteringModeSpec(key="grid_loads", source="grid_power", component=Component.GRID, flows=GRID_FLOWS),
        MeteringModeSpec(
            key="critical_loads", source="internal_meter_power", component=Component.INTERNAL_METER, flows=GRID_FLOWS
        ),
        MeteringModeSpec(
            key="off_grid",
            source="internal_meter_power",
            component=Component.GENERATOR,
            flows=(
                FlowSpec(
                    power_key="generator_power",
                    power_role=Role.GENERATOR_POWER,
                    energy_key="generator_energy",
                    energy_role=Role.ENERGY_GENERATOR,
                    sign=SignFilter.POSITIVE,
                ),
            ),
        ),
    ),
```

Traducciones `entity.sensor`, junto a `grid_import_energy`: en `strings.json` y `en.json`
`"grid_import_power": {"name": "Grid import power"}`, `"grid_export_power": {"name": "Grid export power"}`,
`"generator_power": {"name": "Generator power"}`, `"generator_energy": {"name": "Generator energy"}`; en `es.json`
«Potencia de red», «Potencia a la red», «Potencia del generador», «Energía del generador».

`test_profiles.py` ya pasa `validate_profile` sobre todos los perfiles: debe seguir en verde.

- [ ] **Step 4:** lint; commit `feat: storage metering modes`; ci-wait → verde (incluido `tests/ha/test_energy.py`, que
  sigue integrando `grid_power` en el modo por defecto).

---

### Tarea 5: sensor de potencia derivada, runtime y modo en el setup

**Files:**
- Create: `adapters/inbound/entities/derived.py`
- Modify: `adapters/inbound/entities/factory.py:93-104`, `adapters/inbound/entities/base.py:44-49`,
  `adapters/inbound/runtime.py:51-62`, `const.py`, `__init__.py:56-66`
- Test: `tests/ha/test_sensor.py`, `tests/ha/test_energy.py`, `tests/ha/test_init.py`, `tests/ha/test_coordinator.py`

**Interfaces:**
- Consumes: `Selection.powers`, `select(..., metering)`, `chosen_components(..., metering)`, `filter_power`.
- Produces: `CONF_METERING = "metering"` en `const.py`; `ModbusSolarDerivedPowerSensor(coordinator, runtime, spec)`.

- [ ] **Step 1: tests que fallan**

`tests/ha/common.py`: añadir parámetro `metering: str | None = None` a `setup_storage_entry`; si no es `None`,
`data["metering"] = metering`.

`tests/ha/test_sensor.py` (importar `ModbusConnectionError`, `MockModbusUnit`, `STORAGE_DATA`, `tick`):

```python
async def test_grid_powers_from_external_meter(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    entry = await setup_storage_entry(hass, components=None)
    # grid_power = -300 W: exporta
    assert float(state_of(hass, "grid_import_power").state) == 0
    assert float(state_of(hass, "grid_export_power").state) == 300
    power = state_of(hass, "grid_import_power")
    assert (power.attributes["unit_of_measurement"], power.attributes["device_class"]) == ("W", "power")
    assert power.attributes["state_class"] == "measurement"
    registry_entry = er.async_get(hass).async_get(entity_id_of(hass, "grid_import_power"))
    assert registry_entry.device_id == device_of(hass, entry.entry_id, "_grid").id
    storage_unit.input[71] = 450
    await tick(hass, 6)
    assert float(state_of(hass, "grid_import_power").state) == 450
    assert float(state_of(hass, "grid_export_power").state) == 0


async def test_derived_power_unavailable_without_source(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    await setup_storage_entry(hass, components=None)
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await tick(hass, 6)
    assert state_of(hass, "grid_import_power").state == "unavailable"


async def test_critical_loads_mode_uses_internal_meter(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    # 30052 (dirección 51) = -1200 W
    storage_unit.input[51] = 0x10000 - 1200
    entry = await setup_storage_entry(hass, components=["battery"], metering="critical_loads")
    assert float(state_of(hass, "grid_export_power").state) == 1200
    registry = er.async_get(hass)
    meter = device_of(hass, entry.entry_id, "_internal_meter")
    for key in ("grid_export_power", "grid_import_energy"):
        assert registry.async_get(entity_id_of(hass, key)).device_id == meter.id, key
    # sin Red marcada, el modo no la fuerza
    assert device_of(hass, entry.entry_id, "_grid") is None


async def test_off_grid_mode_creates_generator(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["battery"], metering="off_grid")
    generator = device_of(hass, entry.entry_id, "_generator")
    assert generator is not None and generator.name == "Generator"
    assert state_of(hass, "generator_power") is not None
    assert entity_id_of(hass, "grid_import_power") is None
    assert entity_id_of(hass, "grid_import_energy") is None
```

`tests/ha/test_energy.py` (importar `setup_storage_entry` de `tests.ha.common` y `MockModbusUnit`):

```python
async def test_energy_integrates_the_mode_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    # vatímetro interno exporta 600 W; el externo (-300 W) no cuenta
    storage_unit.input[51] = 0x10000 - 600
    await setup_storage_entry(hass, components=None, metering="critical_loads")
    await advance(hass, freezer, 6)
    assert kwh(hass, "grid_export_energy") == pytest.approx(600 * 6 / 3_600_000)
    assert kwh(hass, "grid_import_energy") == 0
```

`tests/ha/test_init.py`, `test_entry_without_components_loads_all_optional`: sumar `+ len(selection.powers)` a
`expected`.

`tests/ha/test_coordinator.py`: añadir un test de `enabled_keys` con una `Selection` (importar `select`):

```python
async def test_enabled_derived_power_reads_its_source(hass: HomeAssistant) -> None:
    registry = er.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, entry_id=DEVICE_ID)
    entry.add_to_hass(hass)
    # sensor de red y energías desactivados: la potencia derivada activa sigue pidiendo grid_power
    for key in ("grid_power", "grid_import_energy", "grid_export_energy"):
        registry.async_get_or_create(
            "sensor", DOMAIN, f"{DEVICE_ID}_{key}", config_entry=entry, disabled_by=er.RegistryEntryDisabler.USER
        )
    assert "grid_power" in enabled_keys(registry, DEVICE_ID, select(ONEPLAY_STORAGE, None))
```

Antes de escribirlo, leer `tests/ha/test_coordinator.py:80-145` y copiar su forma de crear la entry y los imports
(si ya existe un helper, usarlo en vez de `MockConfigEntry` directo).

- [ ] **Step 2:** lint; commit `test(red): derived power sensors and metering mode on setup`; ci-wait → rojo.

- [ ] **Step 3: implementación**

`const.py`: `CONF_METERING = "metering"` junto a `CONF_COMPONENTS`, con el comentario
`# modo de medición de red; ausente = el primero del perfil`.

`adapters/inbound/entities/derived.py`:

```python
"""Potencia derivada: la fuente leída filtrada por signo (importada, exportada, generador)."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfPower

from ....domain.energy import filter_power
from ....domain.metering import DerivedPowerSpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


class ModbusSolarDerivedPowerSensor(ModbusSolarEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: DerivedPowerSpec) -> None:
        super().__init__(coordinator, runtime, spec)
        self._power = spec

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data is None:
            return None
        value = data.values.get(self._power.source)
        # una fuente sin valor (decode o lectura fallida) deja la potencia sin valor
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        return filter_power(float(value), self._power.sign)
```

`adapters/inbound/entities/base.py`: importar `DerivedPowerSpec` y ampliar el tipo de `spec` en
`ModbusSolarEntity.__init__` a `EntitySpec | EnergySpec | GatedLimitSpec | DerivedPowerSpec`.

`adapters/inbound/entities/factory.py`, al final de `build_sensors`, antes del `return`:

```python
    for power in runtime.selection.powers:
        # la potencia derivada se actualiza con el coordinator de su fuente
        coordinator = runtime.coordinators[by_key[power.source].poll]
        sensors.append(ModbusSolarDerivedPowerSensor(coordinator, runtime, power))
```

`adapters/inbound/runtime.py`, en `enabled_keys` tras el bucle de energías (`DeviceProfile` no tiene `powers`):

```python
    powers = selection.powers if isinstance(selection, Selection) else ()
    for power in powers:
        # una potencia derivada activa necesita leer su fuente
        if _is_enabled(registry, Platform.SENSOR, entry_id, power.key, power.enabled_default):
            keys.add(power.source)
```

`__init__.py`, en `async_setup_entry`: importar `CONF_METERING`;
`metering = data.get(CONF_METERING)  # None: entry sin modo, el primero del perfil`;
`selection = select(profile, requested, metering)`; `chosen = chosen_components(profile, requested, metering)`.

- [ ] **Step 4:** lint; commit `feat: derived power sensors and metering mode on setup`; ci-wait → verde.

---

### Tarea 6: limpieza del registro al cambiar de modo

**Files:**
- Modify: `__init__.py:28-53` (`_remove_unselected`)
- Test: `tests/ha/test_init.py`

**Interfaces:**
- Consumes: `profile.metering_modes`, `Selection.powers`, `chosen` con los componentes del modo (Tarea 5).

- [ ] **Step 1: tests que fallan** — `tests/ha/test_init.py`:

```python
async def switch_mode(hass: HomeAssistant, entry: MockConfigEntry, metering: str) -> None:
    hass.config_entries.async_update_entry(entry, data=entry.data | {"metering": metering})
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)


def unique_ids(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    return {e.unique_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)}


def has_device(hass: HomeAssistant, entry: MockConfigEntry, component: str) -> bool:
    wanted = (DOMAIN, f"{entry.entry_id}_{component}")
    return any(wanted in d.identifiers for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id))


async def test_switch_to_internal_meter_keeps_energy_and_moves_it(
    hass: HomeAssistant, patch_storage_unit: MagicMock
) -> None:
    entry = await setup_storage_entry(hass, components=["grid"])
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_grid_import_energy")
    await switch_mode(hass, entry, "critical_loads")
    # mismo unique_id y entity_id: conserva el historial
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_grid_import_energy") == entity_id
    meter = next(
        d
        for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
        if (DOMAIN, f"{entry.entry_id}_internal_meter") in d.identifiers
    )
    assert registry.async_get(entity_id).device_id == meter.id


async def test_switch_to_off_grid_removes_grid_flows(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["grid"])
    await switch_mode(hass, entry, "off_grid")
    ids = unique_ids(hass, entry)
    for key in ("grid_import_power", "grid_export_power", "grid_import_energy", "grid_export_energy"):
        assert f"{entry.entry_id}_{key}" not in ids, key
    assert f"{entry.entry_id}_generator_energy" in ids
    assert has_device(hass, entry, "generator")


async def test_leaving_off_grid_removes_generator(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    entry = await setup_storage_entry(hass, components=["grid"], metering="off_grid")
    await switch_mode(hass, entry, "grid_loads")
    ids = unique_ids(hass, entry)
    assert f"{entry.entry_id}_generator_power" not in ids
    assert f"{entry.entry_id}_generator_energy" not in ids
    assert not has_device(hass, entry, "generator")
```

- [ ] **Step 2:** lint; commit `test(red): registry cleanup on metering mode change`; ci-wait → rojo
  (`test_switch_to_off_grid_removes_grid_flows` y `test_leaving_off_grid_removes_generator`; el primero puede pasar
  ya: anotarlo en el informe).

- [ ] **Step 3: implementación** — en `_remove_unselected`:

```python
    modes = profile.metering_modes
    # las claves de todos los modos son de la integración aunque el modo actual no las use
    flow_keys = {key for mode in modes for flow in mode.flows for key in (flow.power_key, flow.energy_key)}
    all_keys = (
        {e.key for e in profile.entities}
        | {e.key for e in profile.energies}
        | {c.key for c in profile.controls}
        | flow_keys
    )
    kept = (
        {e.key for e in selection.entities}
        | {e.key for e in selection.energies}
        | {c.key for c in selection.controls}
        | {p.key for p in selection.powers}
    )
```

y los dispositivos:

```python
    # componentes opcionales y dispositivos que solo crea un modo (Generador)
    optional = {spec.component for spec in profile.components} | {mode.component for mode in modes}
    gone = {(DOMAIN, f"{entry.entry_id}_{component}") for component in optional if component not in chosen}
```

- [ ] **Step 4:** lint; commit `feat: remove entities and devices of unused metering modes`; ci-wait → verde.

---

### Tarea 7: paso `metering` en el alta y componente forzado

**Files:**
- Modify: `adapters/inbound/flow.py` (`entity_list`, `DeviceConfigFlow`: `async_step_model`, `_switch_profile`,
  `async_step_connection`, nuevo `async_step_metering`, `async_step_components`, `_show_components`,
  `async_step_readings`, `_show_intervals`, `async_step_intervals`)
- Modify: `strings.json`, `translations/en.json`, `translations/es.json`
- Test: `tests/ha/test_config_flow.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: `metering_mode`, `required_component`, `select(..., metering)`, `CONF_METERING`.
- Produces: atributo `_metering: str | None = None` en `DeviceConfigFlow`; `_show_metering(step_id, profile,
  default)`; `_show_components(step_id, profile, default, metering, *, missing=False)`;
  `_show_intervals(..., metering)` (parámetro nuevo tras `components`). La Tarea 8 los reutiliza.

- [ ] **Step 1: tests que fallan**

`tests/ha/test_config_flow.py`, helpers:

```python
async def to_metering(hass: HomeAssistant) -> dict[str, Any]:
    """Alta del STORAGE hasta el paso de medición de red."""
    result = await start(hass, "ingeteam_oneplay_storage")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "metering")
    return result


async def to_components(hass: HomeAssistant, metering: str = "grid_loads") -> dict[str, Any]:
    """Alta del STORAGE hasta el paso de componentes."""
    result = await configure(hass, await to_metering(hass), {"metering": metering})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "components")
    return result
```

(`to_components` sustituye a la actual; `configure` está definida más abajo en el fichero: mover `configure` encima
de `to_metering`.)

Tests nuevos:

```python
async def test_metering_step_dropdown(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_metering(hass)
    selector = result["data_schema"].schema["metering"]
    assert [o["value"] for o in selector.config["options"]] == ["grid_loads", "critical_loads", "off_grid"]
    assert (selector.config["mode"], selector.config["translation_key"]) == ("dropdown", "metering_mode")
    assert field(result, "metering").default() == "grid_loads"


async def test_metering_mode_forces_its_meter(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    # el vatímetro interno sale marcado aunque el perfil lo tenga desmarcado
    result = await to_components(hass, "critical_loads")
    assert field(result, "components").default() == ["pv", "battery", "grid", "internal_meter", "critical_loads", "load"]
    result = await configure(hass, result, {"components": ["battery"]})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "components")
    assert result["errors"] == {"base": "metering_component_required"}
    assert result["description_placeholders"].items() >= {
        "component": "Internal meter",
        "mode": "Loads on Critical Loads",
    }.items()
    # el formulario conserva lo marcado
    assert field(result, "components").default() == ["battery"]


async def test_off_grid_entry_saves_mode(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass, "off_grid")
    result = await configure(hass, result, {"components": ["battery", "internal_meter"]})
    result = await choose(hass, result, "name")
    result = await configure(hass, result, {"name": "Cabin", "device_id": 0})
    # sin Red no hay tier instant
    result = await create(hass, result, {k: v for k, v in STORAGE_INTERVALS.items() if k != "instant"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (result["data"]["metering"], result["data"]["components"]) == ("off_grid", ["battery", "internal_meter"])


async def test_off_grid_intervals_list_generator(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass, "off_grid")
    result = await configure(hass, result, {"components": ["internal_meter"]})
    result = await choose(hass, result, "name")
    result = await configure(hass, result, {"name": "Cabin", "device_id": 0})
    assert "- Generator · Generator power" in result["description_placeholders"]["fast_entities"]
    assert "- Generator · Generator energy" in result["description_placeholders"]["fast_entities"]


async def test_back_to_connection_keeps_metering(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass, "off_grid")
    result = await configure(hass, result, {"components": ["internal_meter"]})
    result = await choose(hass, result, "connection")
    result = await configure(hass, result, CONNECTION)
    assert result["step_id"] == "metering"
    assert field(result, "metering").default() == "off_grid"
```

Tests existentes que cambian:
- `test_components_step_then_readings_menu`: enviar `{"components": ["grid", "battery"]}`; la última aserción pasa a
  `assert "Solar array" not in readings and "**Grid**" in readings`.
- `test_components_can_be_empty`: borrar (lo sustituye `test_metering_mode_forces_its_meter`).
- `test_back_to_model_forgets_components`: enviar `{"components": ["grid", "battery"]}`; tras `CONNECTION`,
  `assert result["step_id"] == "metering"`, enviar `{"metering": "grid_loads"}` y después la aserción de
  `components` tal como está.
- `test_back_to_connection_keeps_values_and_components`: enviar `{"components": ["grid", "battery"]}`; tras
  `CONNECTION` comprobar `step_id == "metering"`, enviar `{"metering": "grid_loads"}`, y esperar
  `field(result, "components").default() == ["battery", "grid"]` (orden del perfil).
- `test_storage_entry_saves_components_in_profile_order`: enviar `{"components": ["battery", "pv", "grid"]}`; usar
  `create(hass, result, STORAGE_INTERVALS)` (con Red hay tier instant); esperar
  `result["data"]["components"] == ["pv", "battery", "grid"]` y `result["data"]["metering"] == "grid_loads"`.
- `test_intervals_step_storage_lists_entities_by_tier`: el comentario pasa a «3 leídas, 2 potencias y 2 energías
  calculadas»; `assert len(lines) == 7`; añadir `assert "Grid · Grid import power" in instant`.
- `test_add_inverter` (1Play sin modos): comprobar que `"metering" not in result["data"]`.

`tests/unit/test_translations.py`:
- `test_flow_steps_errors_and_aborts_are_translated`: añadir `"metering"` al conjunto de pasos y
  `"metering_component_required"` al de errores.
- añadir:

```python
def test_metering_step_and_modes_are_translated() -> None:
    modes = {m.key for p in ALL_PROFILES for m in p.metering_modes}
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        data = load(name)
        assert set(data["selector"]["metering_mode"]["options"]) == modes, name
        step = data["config"]["step"]["metering"]
        assert step["title"] and step["data"]["metering"] and "{model}" in step["description"], name
        error = data["config"]["error"]["metering_component_required"]
        assert "{component}" in error and "{mode}" in error, name
    labels = {
        "strings.json": ["Loads on Grid", "Loads on Critical Loads", "Off-grid"],
        "translations/es.json": ["Consumos en Grid", "Consumos en Cargas Críticas", "Aislada"],
    }
    for name, expected in labels.items():
        assert list(load(name)["selector"]["metering_mode"]["options"].values()) == expected, name
```

- [ ] **Step 2:** lint; commit `test(red): metering step in the setup flow`; ci-wait → rojo.

- [ ] **Step 3: implementación** — `adapters/inbound/flow.py`

Imports: `CONF_METERING` de `...const`; `metering_mode`, `required_component` de `...application.selection`.

`entity_list`: el orden incluye los dispositivos de modo, y las potencias van con las calculadas:

```python
    # el dispositivo de un modo (Generador) va detrás de los opcionales
    order = (
        Component.MAIN,
        *(c.component for c in profile.components),
        *(m.component for m in profile.metering_modes),
    )
```

```python
    powers = sorted(
        (p for p in selection.powers if poll_of[p.source] is tier), key=lambda p: order.index(p.component)
    )
```

```python
    if powers or energies:
        lines = [line(p.component, "sensor", p.key, p.enabled_default) for p in powers]
        lines += [line(e.component, "sensor", e.key, e.enabled_default) for e in energies]
        parts.append("\n".join([calculated, *lines]))
```

`DeviceConfigFlow`:

```python
    # modo de medición elegido; None = aún sin elegir (el primero del perfil)
    _metering: str | None = None
```

- `async_step_model` y `_switch_profile`: junto a `self._components = None`, `self._metering = None`.
- `async_step_connection`, al validar la sonda: sustituir el bloque `if profile.components: …` por

```python
                if profile.metering_modes:
                    return await self.async_step_metering()
                if profile.components:
                    return await self.async_step_components()
                self._components = []
                return await self.async_step_readings()
```

- Paso nuevo y formulario compartido con reconfigure:

```python
    async def async_step_metering(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        profile = self._profile
        if user_input is not None:
            self._metering = user_input[CONF_METERING]
            if profile.components:
                return await self.async_step_components()
            self._components = []
            return await self.async_step_readings()
        return self._show_metering("metering", profile, self._metering)

    def _show_metering(self, step_id: str, profile: DeviceProfile, default: str | None) -> ConfigFlowResult:
        """Desplegable de modos de medición. Lo comparten el alta y reconfigure."""
        mode = metering_mode(profile, default)
        if mode is None:
            raise RuntimeError(f"{step_id} step without metering modes")
        options = [SelectOptionDict(value=m.key, label=m.key) for m in profile.metering_modes]
        selector = SelectSelector(
            SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN, translation_key="metering_mode")
        )
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required(CONF_METERING, default=mode.key): selector}),
            description_placeholders={"model": profile.models[0]},
        )
```

- Componente forzado. Función de módulo, junto a `check_intervals`:

```python
def missing_meter(profile: DeviceProfile, metering: str | None, chosen: Collection[str]) -> bool:
    """El vatímetro del modo no está entre los componentes marcados."""
    mode = metering_mode(profile, metering)
    return mode is not None and required_component(profile, mode).value not in chosen
```

  (importar `Collection` de `collections.abc`).

- `async_step_components`:

```python
        if user_input is not None:
            chosen = set(user_input[CONF_COMPONENTS])
            if missing_meter(profile, self._metering, chosen):
                return await self._show_components(
                    "components", profile, list(user_input[CONF_COMPONENTS]), self._metering, missing=True
                )
            # en el orden del perfil
            self._components = [c.component for c in profile.components if c.component.value in chosen]
            return await self.async_step_readings()
        ...
        return await self._show_components("components", profile, default, self._metering)
```

- `_show_components`:

```python
    async def _show_components(
        self,
        step_id: str,
        profile: DeviceProfile,
        default: list[str],
        metering: str | None,
        *,
        missing: bool = False,
    ) -> ConfigFlowResult:
        mode = metering_mode(profile, metering)
        wanted = set(default)
        if mode is not None and not missing:
            # el vatímetro del modo sale marcado aunque el perfil lo tenga desmarcado
            wanted.add(required_component(profile, mode).value)
        default = [c.component.value for c in profile.components if c.component.value in wanted]
        options = ...  # sin cambios
        selector = ...  # sin cambios
        translations = await self._translations()
        main = ...  # sin cambios
        placeholders = {"model": profile.models[0], "main": main}
        errors: dict[str, str] = {}
        if missing and mode is not None:
            meter = required_component(profile, mode).value
            prefix = f"component.{DOMAIN}"
            errors["base"] = "metering_component_required"
            placeholders["component"] = translations.get(f"{prefix}.device.{meter}.name", meter)
            placeholders["mode"] = translations.get(f"{prefix}.selector.metering_mode.options.{mode.key}", mode.key)
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required(CONF_COMPONENTS, default=default): selector}),
            errors=errors,
            description_placeholders=placeholders,
        )
```

  Mientras la Tarea 8 no esté hecha, `async_step_reconfigure_components` llama a
  `self._show_components("reconfigure_components", profile, default, self._metering)`.

- `async_step_readings`: `select(self._profile, self._components or [], self._metering)`.
- `_show_intervals`: parámetro nuevo `metering: str | None` tras `components`; `select(profile, components, metering)`.
  Sus dos llamadas pasan `self._metering`.
- `async_step_intervals`: `tiers = present_tiers(select(profile, components, self._metering))`; en `data`, tras
  construirlo:

```python
                mode = metering_mode(profile, self._metering)
                if mode is not None:
                    data[CONF_METERING] = mode.key
```

- `async_step_reconfigure_intervals`: de momento, `select(profile, components, self._metering)` en sus dos usos (la
  Tarea 8 completa el guardado).

Traducciones. `strings.json` y `en.json`:

```json
"metering": {
  "title": "How is the grid measured?",
  "description": "{model}. Choose where the loads of the house are connected. This decides which meter measures the grid exchange and which device holds the grid power and energy.",
  "data": {"metering": "Grid metering"},
  "data_description": {"metering": "Loads on Grid: external meter at the connection point. Loads on Critical Loads: every load on the backup output; the internal meter measures the grid. Off-grid: no grid; the grid terminals may feed a generator."}
}
```

`config.error.metering_component_required`: `"{component} is needed for «{mode}». Tick it or change the grid metering."`

`selector.metering_mode.options`: `{"grid_loads": "Loads on Grid", "critical_loads": "Loads on Critical Loads", "off_grid": "Off-grid"}`.

`es.json`:

```json
"metering": {
  "title": "¿Cómo se mide la red?",
  "description": "{model}. Elige dónde están conectados los consumos de la casa. Así se decide qué vatímetro mide el intercambio con la red y de qué dispositivo cuelgan la potencia y la energía de red.",
  "data": {"metering": "Medición de red"},
  "data_description": {"metering": "Consumos en Grid: vatímetro externo en el punto de conexión. Consumos en Cargas Críticas: todos los consumos en la salida de cargas críticas; el vatímetro interno mide la red. Aislada: sin red; las bornas de red pueden llevar un generador."}
}
```

`config.error.metering_component_required`: `"{component} hace falta para «{mode}». Márcalo o cambia la medición de red."`

`selector.metering_mode.options`: `{"grid_loads": "Consumos en Grid", "critical_loads": "Consumos en Cargas Críticas", "off_grid": "Aislada"}`.

Mantener en `strings.json` y `en.json` el mismo orden de claves; `es.json` con las mismas claves.

- [ ] **Step 4:** lint; commit `feat: metering step in the setup flow`; ci-wait → verde.
- [ ] **Step 5:** `bash scripts/ci-wait.sh validate.yml` → verde (hassfest valida `strings.json` y el selector).

---

### Tarea 8: paso `reconfigure_metering`

**Files:**
- Modify: `adapters/inbound/flow.py` (`async_step_reconfigure`, nuevo `async_step_reconfigure_metering`,
  `async_step_reconfigure_components`, `async_step_reconfigure_intervals`)
- Modify: `strings.json`, `translations/en.json`, `translations/es.json`
- Test: `tests/ha/test_config_flow.py`, `tests/unit/test_translations.py`

**Interfaces:**
- Consumes: `_show_metering`, `_show_components(..., metering, missing=)`, `missing_meter`, `_metering` (Tarea 7).

- [ ] **Step 1: tests que fallan**

`tests/ha/test_config_flow.py`:

```python
async def test_reconfigure_metering_then_components(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry()
    result = await reconfigure(hass, entry)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_metering")
    # entry sin modo guardado: el primero
    assert field(result, "metering").default() == "grid_loads"
    result = await configure(hass, result, {"metering": "critical_loads"})
    assert result["step_id"] == "reconfigure_components"
    assert field(result, "components").default() == ["battery", "internal_meter"]
    result = await configure(hass, result, {"components": ["battery"]})
    assert result["errors"] == {"base": "metering_component_required"}
    result = await configure(hass, result, {"components": ["battery", "internal_meter"]})
    result = await configure(hass, result, {k: v for k, v in STORAGE_INTERVALS.items() if k != "instant"})
    assert result["reason"] == "reconfigure_successful"
    assert (entry.data["metering"], entry.data["components"]) == ("critical_loads", ["battery", "internal_meter"])


async def test_reconfigure_metering_defaults_to_stored(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await reconfigure(hass, storage_entry(metering="off_grid"))
    assert field(result, "metering").default() == "off_grid"
```

Tests existentes que cambian (todos los que hacen reconfigure del STORAGE pasan por el paso nuevo):
- `test_reconfigure_three_steps` → renombrar `test_reconfigure_four_steps`. Tras `reconfigure`, esperar
  `reconfigure_metering` y enviar `{"metering": "grid_loads"}`. El default de componentes pasa a
  `["battery", "grid"]` (Red forzada). El `dict(entry.data)` esperado gana `"metering": "grid_loads"`.
- `test_reconfigure_interval_budget_exceeded`: enviar `{"metering": "grid_loads"}` antes de los componentes.
- `test_reconfigure_entry_without_components_defaults_to_all_optional`: enviar `{"metering": "grid_loads"}` y
  después comprobar `reconfigure_components` con la misma lista.
- `to_rename`: enviar `{"metering": "grid_loads"}` tras la conexión.
- `test_reconfigure_profile_without_components_skips_step` (1Play): `dict(entry.data)` sin `"metering"`.

`tests/unit/test_translations.py`: añadir `"reconfigure_metering"` al conjunto de pasos y:

```python
def test_reconfigure_metering_step_texts() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        step = load(name)["config"]["step"]["reconfigure_metering"]
        assert step["title"] and step["data"]["metering"] and step["submit"], name
        assert "{model}" in step["description"], name
```

- [ ] **Step 2:** lint; commit `test(red): reconfigure metering step`; ci-wait → rojo.

- [ ] **Step 3: implementación** — `adapters/inbound/flow.py`

`async_step_reconfigure`, al validar la sonda: sustituir `if profile.components: …` por

```python
                    if profile.metering_modes:
                        return await self.async_step_reconfigure_metering()
                    if profile.components:
                        return await self.async_step_reconfigure_components()
                    self._components = []
                    return await self.async_step_reconfigure_intervals()
```

Paso nuevo:

```python
    async def async_step_reconfigure_metering(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        profile = self._profile
        if user_input is not None:
            self._metering = user_input[CONF_METERING]
            if profile.components:
                return await self.async_step_reconfigure_components()
            self._components = []
            return await self.async_step_reconfigure_intervals()
        # sin modo guardado (entry anterior), el primero del perfil
        return self._show_metering("reconfigure_metering", profile, entry.data.get(CONF_METERING))
```

`async_step_reconfigure_components`:

```python
        if user_input is not None:
            chosen = set(user_input[CONF_COMPONENTS])
            if missing_meter(profile, self._metering, chosen):
                return await self._show_components(
                    "reconfigure_components", profile, list(user_input[CONF_COMPONENTS]), self._metering, missing=True
                )
            self._components = [c.component for c in profile.components if c.component.value in chosen]
            return await self.async_step_reconfigure_intervals()
```

`async_step_reconfigure_intervals`, tras construir `data` (antes del bucle de `CONF_DEVICE_ID`):

```python
                mode = metering_mode(profile, self._metering)
                if mode is not None:
                    data[CONF_METERING] = mode.key
```

Traducciones `config.step.reconfigure_metering`. `strings.json` y `en.json`:

```json
"reconfigure_metering": {
  "title": "How is the grid measured?",
  "description": "{model}. Between «Loads on Grid» and «Loads on Critical Loads» the grid powers and energies move to the other device and keep their history. Switching to «Off-grid» removes them with their history; leaving «Off-grid» removes the generator ones.",
  "data": {"metering": "Grid metering"},
  "submit": "Next"
}
```

`es.json`:

```json
"reconfigure_metering": {
  "title": "¿Cómo se mide la red?",
  "description": "{model}. Entre «Consumos en Grid» y «Consumos en Cargas Críticas», las potencias y energías de red cambian de dispositivo y conservan su historial. Al pasar a «Aislada» se borran con su historial; al salir de «Aislada» se borran las del generador.",
  "data": {"metering": "Medición de red"},
  "submit": "Siguiente"
}
```

Comprobar en `es.json` cómo se traduce `submit` en `reconfigure_components` y usar la misma palabra.

- [ ] **Step 4:** lint; commit `feat: reconfigure metering step`; ci-wait → verde.
- [ ] **Step 5:** `bash scripts/ci-wait.sh validate.yml` → verde.

---

### Tarea 9: sync de docs

Skill `project-docs`, modo sync. Sin tests nuevos.

- [ ] Actualizar los ficheros de `docs:` de la spec:
  - `docs/features/device-setup.md`: paso «Medición de red», sus tres opciones, componente forzado y aviso de
    reconfigurar.
  - `docs/features/monitoring.md`: potencias de red y del generador; de qué fuente salen las energías de red.
  - `docs/architecture/domain.md`: `domain/metering.py`, `filter_power`, `DeviceProfile.metering_modes`,
    `Component.GENERATOR`, reglas de validación.
  - `docs/architecture/application.md`: `select(..., metering)`, `metering_mode`, `required_component`,
    `Selection.powers`.
  - `docs/architecture/adapters/inbound.md`: `ModbusSolarDerivedPowerSensor`, `enabled_keys`, `_remove_unselected`,
    pasos `metering` y `reconfigure_metering`.
- [ ] ADR nuevo `docs/decisions/0017-metering-mode.md` con el formato de los ADR del repo: el modo de medición decide
  la fuente, las entidades y el dispositivo; elección manual porque no hay registro que identifique el vatímetro.
- [ ] `CHANGELOG.md`: entrada en «Unreleased» (o la sección que use el repo) con la funcionalidad.
- [ ] Spec: `status: done`. Plan: `status: done`. `docs/README.md`: fila del cambio en «cerrado».
- [ ] Verificación en la VM pendiente (spec §9): se deja escrita en la spec, no se ejecuta aquí.
- [ ] lint; commit `docs: grid metering sync`; ci-wait → verde.

## Desviaciones

- **Tarea 4.** Al añadir los modos al perfil, la Red queda forzada y fallaban `test_components_step_then_readings_menu` y `test_storage_entry_saves_components_in_profile_order`. Su adaptación, prevista en la Tarea 7, se adelantó a la Tarea 4 (commit `ebc764f`).
- **Tarea 5.** `filter_power` devolvía `-0.0`, que HA mostraría como «-0.0» en la potencia exportada con `grid_power = 0`. Devuelve `0.0` literal, con un test con `math.copysign`. Efecto: `filter_power(NaN)` da `0.0`.
- **Tarea 6.** `test_off_grid_mode_creates_generator` comprueba también el dispositivo y el valor del generador.
- **Tarea 7.** `test_reconfigure_three_steps` espera `["battery", "grid"]` por defecto antes de la Tarea 8: el arreglo interino ya fuerza la Red.
- **Workspace.** El seguimiento de subagentes va fuera del repo: las reglas del equipo prohíben `.superpowers/` en repos.
