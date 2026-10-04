---
type: feature
area: profiles
layers: [domain, profiles, adapters]
status: done
date: 2026-10-04
---

# Plan de implementación — Spec 4, perfil del sensor de irradiancia Si-RS485TC-…-MB

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `subagent-driven-development` (recomendada) o
> `executing-plans` para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** añadir el perfil `mencke_tegtmeyer.si_rs485` (sensor de irradiancia de Ingenieurbüro
Mencke & Tegtmeyer) con cuatro sensores, la marca nueva en el selector del alta y los textos del
alta sin la palabra «inversor», según `docs/changes/2026-10-04-irradiance-sensor/spec.md`.

**Arquitectura:** el perfil es un literal declarativo más (`DeviceProfile`, ADR 0002) en
`profiles/mencke_tegtmeyer/`, que solo importa `domain`. No hay transporte, plataforma ni
puerto nuevos: el sensor va detrás de una pasarela RS485 → Modbus TCP. `max_gap=3` hace que las
entidades de los registros 0, 3, 7 y 8 se lean en un único bloque FC04 de 9 registros.

**Stack:** Python 3.14, Home Assistant 2026.9.4, `modbus-connection` 4.10.0, pytest +
`pytest-homeassistant-custom-component` 0.13.367, ruff, import-linter, GitHub Actions.

## Global Constraints

- Rama de trabajo: `sigergy/irradiance-sensor`. Nunca commit en `main`.
- **Push, PR y merge piden confirmación del usuario.** Force push y rebase también.
- **Tests solo en GitHub Actions** (ADR 0007). Nunca `pytest` en la máquina Windows. RED y GREEN se
  comprueban con `bash scripts/ci-wait.sh` (hace push), solo con confirmación del usuario. Sin ella,
  se deja el commit RED y se avisa.
- Gates locales antes de cada commit: `bash scripts/lint.sh` (ruff format, ruff check,
  lint-imports y compileall). Si falta `.venv`: `py -3.14 -m venv .venv` y
  `.venv/Scripts/pip install ruff import-linter`. `.venv/` no se commitea.
- Commits RED (`test(red): …`) permitidos en la rama. Un commit GREEN por tarea con CI en verde.
- Todo commit termina con:
  ```
  Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_014vqSEWepdDNsKAh29ybc5z
  ```
- Comentarios del código en español. Identificadores, ficheros, logs y `strings.json` en inglés.
  Ficheros en `snake_case` (Python).
- Dentro de `custom_components/modbus_solar` solo imports relativos.
- Contratos de import-linter intactos: `domain`, `ports`, `application` y `profiles` no importan
  `homeassistant` ni `modbus_connection`.
- Perfil: `min_request_interval_s=1.0`, `max_block_registers=125` (por defecto), `max_gap=3`, todo
  `RegisterKind.INPUT` (FC04), puerto 502, unit ID 1 (`Specification_Si-RS485_MODBUS.pdf` págs. 1 y
  5; spec §3).
- Los registros 7 y 8 exigen firmware ≥ 1.53 (`Specification` pág. 1).
- No tocar nombres de entidad Ingeteam ni `exceptions.write_failed` (`strings.json`).
- `graft/`, `.graft_*`, `.venv/` y `.ignore` nunca se commitean.
- No inventar: cita `archivo:línea` o página del PDF. Si una API no se comporta como dice el plan,
  parar y avisar con la salida real.
- Prohibido `docs/superpowers/`.

## Mapa de ficheros

| Fichero | Cambio | Tarea |
|---|---|---|
| `strings.json`, `translations/en.json`, `translations/es.json` | «inverter» → «device»; cuatro nombres de entidad | 1 |
| `tests/unit/test_translations.py` | test de textos del alta y de nombres del sensor | 1 |
| `const.py` | `BRAND_TITLES` + `mencke_tegtmeyer` | 2 |
| `domain/types.py` | cuatro roles nuevos | 2 |
| `profiles/mencke_tegtmeyer/__init__.py` | nuevo, vacío salvo docstring | 2 |
| `profiles/mencke_tegtmeyer/si_rs485.py` | nuevo: `SI_RS485` | 2 |
| `profiles/__init__.py` | `ALL_PROFILES` incluye `SI_RS485` | 2 |
| `tests/unit/test_si_rs485_profile.py` | nuevo | 2 |
| `tests/unit/test_profiles.py` | catálogo con dos marcas | 2 |
| `tests/ha/test_config_flow.py` | selector con la marca nueva | 2 |
| `docs/wiki/brands/mencke-tegtmeyer/README.md`, `si-rs485-mb/registers.md` | nuevos | 3 |
| `docs/decisions/0013-…md` | nuevo ADR | 3 |
| `docs/features/monitoring.md`, `docs/architecture/domain.md`, `docs/README.md`, `README.md` | documentación | 3 |
| `docs/changes/2026-10-04-irradiance-sensor/spec.md`, `plan.md` | `status: done` | 3 |

Rutas de código relativas a `custom_components/modbus_solar/`, salvo `tests/` y `docs/`.

---

### Tarea 1: textos del alta sin «inversor» y nombres del sensor

**Files:**
- Modify: `strings.json:6`, `:12-13`, `:28-29`; `translations/en.json` (copia literal);
  `translations/es.json:6`, `:12-13`, `:28-29`
- Test: `tests/unit/test_translations.py`

**Interfaces:**
- Produces: claves `entity.sensor.irradiance`, `wind_speed`, `cell_temperature` y
  `external_temperature`, cada una con `name`. La Tarea 2 las necesita: el test
  `test_every_entity_and_enum_state_is_translated` (`test_translations.py:32-44`) falla si falta
  alguna cuando el perfil entra en `ALL_PROFILES`.

- [ ] **Step 1: tests que fallan**

Añadir al final de `tests/unit/test_translations.py`:

```python
def test_flow_texts_do_not_say_inverter() -> None:
    # el alta sirve a cualquier equipo (inversor, sensor…): sin «inverter» ni «inversor»
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        for step in ("user", "connection", "confirm"):
            step_texts = load(name)["config"]["step"][step]
            for field in ("title", "description"):
                text = step_texts[field].lower()
                assert "inverter" not in text and "inversor" not in text, f"{name} {step}.{field}"


def test_irradiance_sensor_entities_are_named() -> None:
    expected = {
        "strings.json": {
            "irradiance": "Irradiance",
            "wind_speed": "Wind speed",
            "cell_temperature": "Cell temperature",
            "external_temperature": "External temperature",
        },
        "translations/es.json": {
            "irradiance": "Irradiancia",
            "wind_speed": "Velocidad del viento",
            "cell_temperature": "Temperatura de la célula",
            "external_temperature": "Temperatura externa",
        },
    }
    for name, names in expected.items():
        sensors = load(name)["entity"]["sensor"]
        assert {key: sensors[key]["name"] for key in names} == names, name
```

- [ ] **Step 2:** `bash scripts/lint.sh` y commit
  `test(red): device wording and irradiance sensor names`. Con confirmación del usuario,
  `bash scripts/ci-wait.sh` → rojo en los dos tests nuevos (`AssertionError` por «inverter» y
  `KeyError: 'irradiance'`). Sin confirmación, queda el commit RED y se avisa.

- [ ] **Step 3: implementación**

`strings.json`, en `config.step`:

```json
      "user": {
        "title": "Choose the model",
        "description": "Each device is a separate entry. Add one entry per device.",
```
```json
      "connection": {
        "title": "Connect to the device",
        "description": "Enter the IP address or hostname of the device. The connection is tested before going on.",
```
```json
      "confirm": {
        "title": "Device found",
        "description": "The device at {host} answered:\n\n{readings}",
```

`translations/es.json`, mismas líneas:

```json
        "description": "Cada equipo es una entry independiente. Añade una entry por equipo.",
        "title": "Conectar con el equipo",
        "description": "Escribe la dirección IP o el nombre de host del equipo. La conexión se prueba antes de seguir.",
        "title": "Equipo encontrado",
        "description": "El equipo en {host} ha respondido:\n\n{readings}",
```

Añadir en `entity.sensor` de `strings.json`, tras `battery_discharge_energy` (con coma en la clave
anterior):

```json
      "irradiance": {
        "name": "Irradiance"
      },
      "wind_speed": {
        "name": "Wind speed"
      },
      "cell_temperature": {
        "name": "Cell temperature"
      },
      "external_temperature": {
        "name": "External temperature"
      }
```

En `translations/es.json`, en la misma posición:

```json
      "irradiance": {
        "name": "Irradiancia"
      },
      "wind_speed": {
        "name": "Velocidad del viento"
      },
      "cell_temperature": {
        "name": "Temperatura de la célula"
      },
      "external_temperature": {
        "name": "Temperatura externa"
      }
```

`translations/en.json` se regenera como copia literal de `strings.json`
(`test_en_is_literal_copy_of_strings`, `test_translations.py:24-25`):

```bash
cp custom_components/modbus_solar/strings.json custom_components/modbus_solar/translations/en.json
```

- [ ] **Step 4:** `bash scripts/lint.sh`; con confirmación, `bash scripts/ci-wait.sh` → verde.

- [ ] **Step 5: commit**

```bash
git add custom_components/modbus_solar/strings.json custom_components/modbus_solar/translations tests/unit/test_translations.py
git commit -m "feat: device wording in the config flow and irradiance sensor names"
```

(con el trailer de Global Constraints).

---

### Tarea 2: marca, roles, perfil y catálogo

**Files:**
- Create: `profiles/mencke_tegtmeyer/__init__.py`, `profiles/mencke_tegtmeyer/si_rs485.py`,
  `tests/unit/test_si_rs485_profile.py`
- Modify: `const.py:12`, `domain/types.py:59-60`, `profiles/__init__.py:3-7`,
  `tests/unit/test_profiles.py:67-71`, `tests/ha/test_config_flow.py:47-50`

**Interfaces:**
- Consumes: claves de traducción de la Tarea 1; `DeviceProfile`, `EntitySpec`, `RegisterSpec`
  (`domain/profile.py`); `plan_blocks(registers, max_gap, max_count) -> list[Block]`
  (`domain/blocks.py:16`); `min_tier_interval(profile, tier) -> float` (`application/poller.py:46`);
  `decode(spec, words)` (`domain/decode.py`).
- Produces: `SI_RS485: DeviceProfile` en `profiles/mencke_tegtmeyer/si_rs485.py`;
  `Role.IRRADIANCE`, `Role.WIND_SPEED`, `Role.CELL_TEMPERATURE`, `Role.EXTERNAL_TEMPERATURE`;
  `BRAND_TITLES["mencke_tegtmeyer"]`.

- [ ] **Step 1: tests que fallan**

Crear `tests/unit/test_si_rs485_profile.py`:

```python
"""Perfil Si-RS485TC-…-MB de Ingenieurbüro Mencke & Tegtmeyer (sensor de irradiancia)."""

import pytest

from custom_components.modbus_solar.application.poller import min_tier_interval
from custom_components.modbus_solar.domain.blocks import Block, plan_blocks
from custom_components.modbus_solar.domain.decode import decode
from custom_components.modbus_solar.domain.types import DataType, Platform, PollTier, RegisterKind, Role
from custom_components.modbus_solar.domain.validate import validate_profile
from custom_components.modbus_solar.profiles import ALL_PROFILES
from custom_components.modbus_solar.profiles.mencke_tegtmeyer.si_rs485 import SI_RS485

KEYS = ["irradiance", "wind_speed", "cell_temperature", "external_temperature"]


def entity(key: str):
    return next(e for e in SI_RS485.entities if e.key == key)


def test_identity_and_limits() -> None:
    p = SI_RS485
    assert (p.id, p.brand, p.device_type, p.models) == (
        "mencke_tegtmeyer.si_rs485",
        "mencke_tegtmeyer",
        "irradiance_sensor",
        ("Si-RS485TC-T-MB", "Si-RS485TC-2T-MB", "Si-RS485TC-2T-v-MB", "Si-RS485TC-T-Tm-MB"),
    )
    # Specification pág. 1: sin mínimo entre peticiones; 1 s como en Ingeteam (supuesto, spec §3.1)
    assert (p.min_request_interval_s, p.max_block_registers, p.max_gap) == (1.0, 125, 3)
    # Specification pág. 1: dirección 1 de fábrica; el puerto es el de la pasarela Modbus TCP
    assert (p.default_port, p.default_unit_id, p.probe_key) == (502, 1, "irradiance")
    assert validate_profile(p) == []
    assert SI_RS485 in ALL_PROFILES


def test_entities_are_the_four_sensors() -> None:
    assert [e.key for e in SI_RS485.entities] == KEYS
    assert [e.role for e in SI_RS485.entities] == [
        Role.IRRADIANCE,
        Role.WIND_SPEED,
        Role.CELL_TEMPERATURE,
        Role.EXTERNAL_TEMPERATURE,
    ]
    assert SI_RS485.energies == ()
    assert SI_RS485.controls == ()


def test_all_entities_are_fast_enabled_input_sensors() -> None:
    for e in SI_RS485.entities:
        assert e.platform is Platform.SENSOR, e.key
        assert e.register.kind is RegisterKind.INPUT, e.key
        assert e.poll is PollTier.FAST, e.key
        assert e.enabled_default, e.key
        assert e.entity_category is None, e.key
        assert e.state_class == "measurement", e.key


@pytest.mark.parametrize(
    ("key", "address", "dtype", "device_class", "unit"),
    [
        # Specification pág. 1: registros 0000, 0003, 0007 y 0008, ganancia 0.1 y offset 0
        ("irradiance", 0, DataType.U16, "irradiance", "W/m²"),
        ("wind_speed", 3, DataType.U16, "wind_speed", "m/s"),
        ("cell_temperature", 7, DataType.S16, "temperature", "°C"),
        ("external_temperature", 8, DataType.S16, "temperature", "°C"),
    ],
)
def test_registers_match_pdf(key: str, address: int, dtype: DataType, device_class: str, unit: str) -> None:
    e = entity(key)
    assert (e.register.address, e.register.dtype, e.register.scale, e.register.offset) == (address, dtype, 0.1, 0)
    assert (e.device_class, e.unit) == (device_class, unit)


def test_one_read_block_for_all_entities() -> None:
    registers = [e.register for e in SI_RS485.entities]
    assert plan_blocks(registers, SI_RS485.max_gap, SI_RS485.max_block_registers) == [Block(RegisterKind.INPUT, 0, 9)]
    assert min_tier_interval(SI_RS485, PollTier.FAST) == 1.0


def test_negative_cell_temperature_keeps_its_sign() -> None:
    # raw 0xFFCE = -50 → -5.0 °C
    assert decode(entity("cell_temperature"), (0xFFCE,)) == -5.0
    assert decode(entity("irradiance"), (1234,)) == 123.4
```

`tests/unit/test_profiles.py`, importar el perfil y sustituir `test_catalog_lookup`:

```python
from custom_components.modbus_solar.profiles.mencke_tegtmeyer.si_rs485 import SI_RS485
```

```python
def test_catalog_lookup() -> None:
    assert CATALOG.brands() == ["ingeteam", "mencke_tegtmeyer"]
    assert CATALOG.for_brand("ingeteam") == [ONEPLAY, ONEPLAY_STORAGE]
    assert CATALOG.for_brand("mencke_tegtmeyer") == [SI_RS485]
    assert CATALOG.for_brand("other") == []
    assert CATALOG.get("ingeteam.oneplay") is ONEPLAY
    assert CATALOG.get("ingeteam.oneplay_storage") is ONEPLAY_STORAGE
    assert CATALOG.get("mencke_tegtmeyer.si_rs485") is SI_RS485
    with pytest.raises(KeyError):
        CATALOG.get("missing")
```

`tests/ha/test_config_flow.py`, en `test_model_step_lists_every_profile` (línea 47-50):

```python
    assert selector.config["options"] == [
        {"value": "ingeteam.oneplay", "label": "Ingeteam · 1Play TL M"},
        {"value": "ingeteam.oneplay_storage", "label": "Ingeteam · STORAGE 1Play TL M"},
        {
            "value": "mencke_tegtmeyer.si_rs485",
            "label": (
                "Ingenieurbüro Mencke & Tegtmeyer · "
                "Si-RS485TC-T-MB, Si-RS485TC-2T-MB, Si-RS485TC-2T-v-MB, Si-RS485TC-T-Tm-MB"
            ),
        },
    ]
```

- [ ] **Step 2:** `bash scripts/lint.sh` y commit `test(red): irradiance sensor profile`. Con
  confirmación del usuario, `bash scripts/ci-wait.sh` → rojo por
  `ModuleNotFoundError: No module named 'custom_components.modbus_solar.profiles.mencke_tegtmeyer'`
  en los tests nuevos y en `test_profiles.py`, y por la lista de opciones en `test_config_flow.py`.
  Sin confirmación, queda el commit RED y se avisa.

- [ ] **Step 3: implementación**

`const.py:12`:

```python
BRAND_TITLES = {"ingeteam": "Ingeteam", "mencke_tegtmeyer": "Ingenieurbüro Mencke & Tegtmeyer"}
```

`domain/types.py`, al final de `Role`, tras `EXPORT_ENABLED = "export_enabled"`:

```python
    IRRADIANCE = "irradiance"
    WIND_SPEED = "wind_speed"
    CELL_TEMPERATURE = "cell_temperature"
    EXTERNAL_TEMPERATURE = "external_temperature"  # ambiente o módulo, según el modelo
```

`profiles/mencke_tegtmeyer/__init__.py`:

```python
"""Perfiles de Ingenieurbüro Mencke & Tegtmeyer."""
```

`profiles/mencke_tegtmeyer/si_rs485.py`:

```python
"""Sensor de irradiancia Si-RS485TC-…-MB. Fuente: Specification_Si-RS485_MODBUS.pdf
(docs/wiki/brands/mencke-tegtmeyer/si-rs485-mb/)."""

from ...domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from ...domain.types import DataType, Platform, PollTier, RegisterKind, Role

SI_RS485 = DeviceProfile(
    id="mencke_tegtmeyer.si_rs485",
    brand="mencke_tegtmeyer",
    device_type="irradiance_sensor",
    models=("Si-RS485TC-T-MB", "Si-RS485TC-2T-MB", "Si-RS485TC-2T-v-MB", "Si-RS485TC-T-Tm-MB"),
    # el PDF no fija un mínimo entre peticiones: 1 s como en Ingeteam (supuesto)
    min_request_interval_s=1.0,
    # los registros 0, 3, 7 y 8 quedan a huecos de hasta 3: un solo bloque de 9 registros; los
    # huecos existen y se leen sin error (págs. 1-2)
    max_gap=3,
    # pág. 1: dirección 1 de fábrica; el puerto es el de la pasarela RS485 → Modbus TCP
    default_port=502,
    default_unit_id=1,
    probe_key="irradiance",
    entities=(
        EntitySpec(
            key="irradiance",
            role=Role.IRRADIANCE,
            platform=Platform.SENSOR,
            # pág. 1: registro 0000, UINT16, ganancia 0.1, 0…1500 W/m²
            register=RegisterSpec(address=0, kind=RegisterKind.INPUT, dtype=DataType.U16, scale=0.1),
            poll=PollTier.FAST,
            device_class="irradiance",
            state_class="measurement",
            unit="W/m²",
        ),
        EntitySpec(
            key="wind_speed",
            role=Role.WIND_SPEED,
            platform=Platform.SENSOR,
            # pág. 1: registro 0003, UINT16, ganancia 0.1; opcional: sin sensor devuelve 0
            register=RegisterSpec(address=3, kind=RegisterKind.INPUT, dtype=DataType.U16, scale=0.1),
            poll=PollTier.FAST,
            device_class="wind_speed",
            state_class="measurement",
            unit="m/s",
        ),
        EntitySpec(
            key="cell_temperature",
            role=Role.CELL_TEMPERATURE,
            platform=Platform.SENSOR,
            # pág. 1: registro 0007, INT16, ganancia 0.1; exige firmware >= 1.53
            register=RegisterSpec(address=7, kind=RegisterKind.INPUT, dtype=DataType.S16, scale=0.1),
            poll=PollTier.FAST,
            device_class="temperature",
            state_class="measurement",
            unit="°C",
        ),
        EntitySpec(
            key="external_temperature",
            role=Role.EXTERNAL_TEMPERATURE,
            platform=Platform.SENSOR,
            # pág. 1: registro 0008 (temperatura externa 1), INT16, ganancia 0.1; firmware >= 1.53;
            # opcional. Según el modelo mide el ambiente o el módulo (pág. 5)
            register=RegisterSpec(address=8, kind=RegisterKind.INPUT, dtype=DataType.S16, scale=0.1),
            poll=PollTier.FAST,
            device_class="temperature",
            state_class="measurement",
            unit="°C",
        ),
    ),
)
```

`profiles/__init__.py`:

```python
from .ingeteam.oneplay import ONEPLAY
from .ingeteam.oneplay_storage import ONEPLAY_STORAGE
from .mencke_tegtmeyer.si_rs485 import SI_RS485

ALL_PROFILES: tuple[DeviceProfile, ...] = (ONEPLAY, ONEPLAY_STORAGE, SI_RS485)
```

- [ ] **Step 4:** `bash scripts/lint.sh` (ruff format, ruff check, lint-imports, compileall: sin
  salida de error). Con confirmación, `bash scripts/ci-wait.sh` → verde en toda la suite, también
  `test_translations.py` (los nombres de la Tarea 1 cubren las cuatro entidades).

- [ ] **Step 5: commit**

```bash
git add custom_components/modbus_solar tests
git commit -m "feat: irradiance sensor profile and Mencke & Tegtmeyer brand"
```

(con el trailer de Global Constraints).

---

### Tarea 3: documentación y cierre

**Files:**
- Create: `docs/wiki/brands/mencke-tegtmeyer/README.md`,
  `docs/wiki/brands/mencke-tegtmeyer/si-rs485-mb/registers.md`,
  `docs/decisions/0013-sensor-series-profile.md`
- Modify: `docs/features/monitoring.md`, `docs/architecture/domain.md:14`, `docs/README.md`,
  `README.md`, `docs/changes/2026-10-04-irradiance-sensor/spec.md` y `plan.md` (`status: done`)
- Los PDF ya están en `docs/wiki/brands/mencke-tegtmeyer/si-rs485-mb/` (SHA-256 verificados contra
  los originales).

**Interfaces:**
- Consumes: el perfil y los roles de la Tarea 2. Los docs describen lo que ya está en el código;
  ninguna afirmación sin `archivo:línea` o página del PDF.

- [ ] **Step 1: `README.md` del wiki de la marca.** Copiar la estructura de
  `docs/wiki/brands/ingeteam/README.md`: qué hay en la carpeta, procedencia, SHA-256 y revisión de
  cada PDF (ADR 0006):
  - `Specification_Si-RS485_MODBUS.pdf` — `689d0c20131150fe86f0b1e6e199643828538a75e46f6864a6fc6fa9ee1255fa`,
    especificación de feb 2022, firmware 2.01.
  - `Si_Instruction_digital_2017_E_SP.pdf` — `797d4cf9d0cb32ee09ae0f422ec3f8c75c052b40a236d025e94874a8e35c8d01`,
    guía rápida (el pie del PDF indica nov 2019).
  - Origen de la descarga: «sin registrar» (pendiente de anotar la URL de ib-mut.de).

- [ ] **Step 2: `si-rs485-mb/registers.md`.** Seguir
  `docs/wiki/brands/ingeteam/storage-1-play-tl-m/registers.md`: tabla de los registros 0000, 0003,
  0007 y 0008 con página, tipo, ganancia, rango y entidad del perfil; registros activos por modelo
  (`Specification` pág. 5); registros no usados (0001, 0002, 0004, 0005, 0006, 0009) con su motivo;
  aviso de que los registros 7 y 8 exigen firmware ≥ 1.53; un registro opcional ausente devuelve 0,
  no error (pág. 1); discrepancias: 38400 baudios máximos en la guía frente a 57600 en la
  especificación, y la fecha de la guía (2017 en el nombre, 2019 en el pie).

- [ ] **Step 3: ADR `docs/decisions/0013-sensor-series-profile.md`.** Front-matter como los demás
  (`status: accepted`, `date: 2026-10-04`); secciones Contexto / Decisión / Consecuencias:
  un perfil por serie cuando los modelos comparten tabla de registros y los opcionales devuelven 0
  (`Specification` pág. 1); todas las entidades activas por defecto; consecuencia: lecturas falsas de
  0 en los modelos sin viento o sin temperatura externa, mitigadas deshabilitando la entidad. Salida
  futura: leer el modelo por FC 0x46 o un perfil por modelo.

- [ ] **Step 4: resto de docs.**
  - `docs/features/monitoring.md`: sección «Sensor de irradiancia» con las cuatro entidades, el
    bloque único de 9 registros y la nota de falsos 0.
  - `docs/architecture/domain.md:14`: añadir los cuatro roles nuevos a la fila de `Role`.
  - `docs/README.md`: fila de este cambio, y la del ADR 0013 si el índice lista los ADR.
  - `README.md`: fila de equipos soportados (Si-RS485TC-…-MB, vía pasarela RS485 → Modbus TCP) y el
    paso de configuración «del equipo» en lugar de «del inversor», si lo dice así.
  - `spec.md` y `plan.md`: `status: done`.

- [ ] **Step 5:** comprobar enlaces y rutas de los docs a mano (`graft grep` o Grep de cada
  ruta citada). `bash scripts/lint.sh` (los docs no pasan por ruff; el gate confirma que el código
  sigue en verde).

- [ ] **Step 6: commit**

```bash
git add docs README.md
git commit -m "docs: irradiance sensor profile, registers and ADR 0013"
```

(con el trailer de Global Constraints). No incluir `graft/`, `.graft_*`, `.venv/` ni `.ignore`.

---

## Verificación final

- [ ] `bash scripts/lint.sh` sin errores y leída la salida completa (skill
  `verification-before-completion`).
- [ ] Con confirmación del usuario, `bash scripts/ci-wait.sh` → verde sobre el último commit. Sin
  confirmación: informar de que los tests no se han ejecutado y por qué (ADR 0007).
- [ ] `git status` sin ficheros ajenos; `git log` con un commit RED y un GREEN por tarea.
- [ ] Informe final: tokens ahorrados por graft, trailer usado (Sonnet 5.5, sesión actual, no la del
  brief), riesgo de falsos 0 (spec §7.1), origen de los PDF sin registrar (§7.7) y las dos
  discrepancias de documentación.
