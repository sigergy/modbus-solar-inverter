---
type: feature
area: core
layers: [domain, application, ports, adapters, profiles]
status: draft
date: 2026-10-04
---

# Spec 0 — Esqueleto de arquitectura de `modbus_solar`

## 1. Objetivo y alcance

Custom integration de Home Assistant, instalable por HACS, que monitoriza (y en specs
posteriores controla) inversores solares y sensores por Modbus TCP. Esta spec construye
**solo el esqueleto**: capas hexagonales, config flow, calidad/CI y empaquetado HACS,
probado de punta a punta con **tres registros** del Ingeteam 1Play Storage.

**Dentro:**
- Paquete `custom_components/modbus_solar` con capas `domain`, `ports`, `application`,
  `adapters`, `profiles` y reglas de dependencia verificadas en CI.
- Config entry por marca (hub) + config subentry por equipo.
- Plataforma `sensor` con 3 entidades del perfil Ingeteam.
- Sondeo por tiers (`fast` / `normal` / `slow`).
- Errores tipados, disponibilidad y `diagnostics`.
- Tests y CI en GitHub Actions; release zip para HACS.
- Documentación según la plantilla de `docs/` y 8 ADR.

**Fuera (specs posteriores):**
- Spec 1: perfil Ingeteam completo de lectura (resto de registros, MPPT, strings, eventos).
- Spec 2: control (`number`, `select`, `switch`) mediante el protocolo de comandos
  AAA0030IMB03 (CMD 24 Battery Commands, CMD 26 Battery Control Values), SOC de batería.
- Spec 3: otros equipos (célula de irradiancia, meters), autodescubrimiento SunSpec.
- Spec 4: frontend (cards de Lovelace y panel lateral por roles semánticos).
- Última fase: export/import de perfiles en JSON.
- Repairs, backoff exponencial, sondeo adaptativo.

**Criterios de éxito:**
1. Desde la UI de HA se añade la marca Ingeteam y un equipo (host, puerto, unit id).
2. Aparecen 3 sensores con valor; la energía es válida para el panel de Energía.
3. Con el equipo apagado, las entidades pasan a `unavailable` y se recuperan solas.
4. El diagnostics del dispositivo muestra raw y valor decodificado de cada entidad.
5. CI en verde en GitHub Actions: jobs `lint` (ruff, import-linter, `compileall`) y
   `test` (pytest sobre `tests/unit` y `tests/ha`), hassfest y validación HACS.

## 2. Contexto técnico verificado

Versión mínima de HA: **2026.9.0** (`hacs.json`).

| Hecho | Fuente |
|---|---|
| `async_get_unit(hass, entry, params, unit_id) -> ModbusUnit` comparte la conexión por endpoint y la libera con `entry.async_on_unload` | HA 2026.9.0 `homeassistant/components/modbus/connection.py:82-100` |
| `async_get_temporary_unit(hass, params, unit_id)` para config flows; cierra al salir si la abrió | `connection.py:103-125` |
| Ambas lanzan `HomeAssistantError` si el endpoint ya está en uso con otros parámetros de enlace | `connection.py:62-65`, `:94-95` |
| El manifest de `modbus` fija `pymodbus==3.13.1`, `modbus-connection[tmodbus]==4.10.0`, `tmodbus==0.6.2` | `homeassistant/components/modbus/manifest.json` |
| `ModbusUnit.read_holding_registers(address, count) -> list[int]` | `modbus_connection/_protocol.py:15` (4.10.0) |
| `ModbusUnit.set_message_spacing(seconds)`: intervalo mínimo entre peticiones a la unit | `modbus_connection/_protocol.py:50-51`, implementado en `_pacing.py` |
| `ModbusTcpParams(host, port=502, framer="socket")` | `modbus_connection/_client.py:29-37` |
| Excepciones: `ModbusConnectionError`, `ModbusTimeoutError`, `ModbusProtocolError`, `ModbusExceptionError` | `modbus_connection/exceptions.py:51-72` |
| Mock en memoria y fixtures pytest `mock_modbus_connection`, `mock_modbus_unit` (plugin `pytest11`) | `modbus_connection/mock.py:76-104`, `pytest_plugin.py:13-21` |
| `ConfigSubentry` solo tiene `data`, `subentry_id`, `subentry_type`, `title`, `unique_id` (sin `options`) | HA 2026.9.0 `config_entries.py:372-379` |
| `ConfigSubentryFlow.async_update_and_abort(..., data_updates=...)` para reconfigure | `config_entries.py:3814-3830` |
| `async_add_entities(..., config_subentry_id=...)` | `helpers/entity_platform.py:147-151` |
| `async_get_device_diagnostics`, `async_redact_data` | `components/diagnostics/__init__.py:101`, `diagnostics/util.py:24` |

**Datos del Ingeteam 1Play Storage** (PDF `ACL2010IMB05`, págs. 4-5 y Nota 3 pág. 7):
- FC03 (holding), solo lectura; un único cliente Modbus en el puerto 502; periodo entre
  peticiones ≥ 1 s.
- Registros de esta spec:

| Dirección | Clave | Tipo | Escala doc | `scale` | Unidad | `device_class` | `state_class` | Tier |
|---|---|---|---|---|---|---|---|---|
| `0x101D` | `inverter_state` | UINT16 | Nota 3 | — | — | `enum` | — | `fast` |
| `0x1037` | `active_power` | INT32 | `[W x 10]` | 0.1 | `W` | `power` | `measurement` | `fast` |
| `0x1021` | `total_energy` | UINT32 | `[Wh x 10]` | 0.1 | `Wh` | `energy` | `total_increasing` | `normal` |

- Enum de `0x101D` (Nota 3): `0x0` → `factory_default`, `0x1` → `grid_disconnected`,
  `0x3` → `grid_connected`. **Solo estos tres.** El `STATUS_MAP` de 10 estados del
  proyecto anterior (`ha-ingeteam-modbus - copia/.../const.py`) no tiene fuente y no se
  reutiliza.

**Supuestos sin verificar (se comprueban en la VM con diagnostics):**
- `[X x 10]` significa raw = valor × 10, es decir, `scale = 0.1`.
- Los 32 bits van con la palabra alta primero (`word_order = "big"`). El PDF no lo dice;
  el proyecto anterior lo supuso sin probarlo (`ha-modbus-solar-inverter/.../__init__.py:227`).

## 3. Arquitectura

### 3.1 Estructura

```
custom_components/modbus_solar/
  __init__.py              raíz de composición: setup/unload de la entry; un runtime por subentry
  config_flow.py           raíz de composición: abre async_get_temporary_unit, construye
                           ModbusGateway y lo inyecta (gateway_factory) en adapters/inbound/flow.py
  diagnostics.py           delega en adapters/inbound/diagnostics.py
  sensor.py                delega en adapters/inbound/entities/factory.py
  manifest.json  strings.json  translations/{es,en}.json
  brand/icon.png           icono de la integración (ver §8)
  const.py                 DOMAIN y claves de config

  domain/                  solo stdlib
    types.py               DataType (u16, s16, u32, s32), RegisterKind (holding, input),
                           PollTier (fast, normal, slow), Role, Platform, WordOrder
    profile.py             RegisterSpec, EntitySpec, DeviceProfile, WriteSpec (vacío)
    decode.py              decode(spec, words) -> int | float | str
    errors.py              DeviceUnavailable, DeviceProtocolError, DecodeError
    validate.py            validate_profile(profile) -> list[str]

  ports/
    device.py              Protocol DeviceGateway

  application/             domain + ports; sin homeassistant ni modbus_connection
    poller.py              read_tier(tier, gateway, profile) -> TierResult
    probe.py               probe_device(gateway, profile): lee profile.probe_key
    catalog.py             Catalog: perfiles por marca e id

  adapters/
    inbound/
      flow.py              BrandFlow, DeviceSubentryFlow
      coordinator.py       TierCoordinator(DataUpdateCoordinator[TierResult])
      diagnostics.py
      entities/factory.py  EntitySpec -> entidad HA
      entities/base.py     ModbusSolarEntity(CoordinatorEntity)
    outbound/
      modbus_gateway.py    ModbusGateway: implementa DeviceGateway sobre ModbusUnit

  profiles/                solo domain
    ingeteam/oneplay_storage.py

tests/
  unit/                    sin fixture `hass`: domain, application, profiles, gateway con mock
  ha/                      con pytest-homeassistant-custom-component
```

### 3.2 Reglas de dependencia (contratos `import-linter`)

| Capa | Puede importar |
|---|---|
| `domain` | solo stdlib |
| `ports` | `domain` |
| `application` | `domain`, `ports` |
| `profiles` | `domain` |
| `adapters` | todo, incluidos `homeassistant` y `modbus_connection` |

Contratos: `layers` (adapters > application > ports > domain), `forbidden`
(`domain`, `ports`, `application` y `profiles` no importan `homeassistant` ni
`modbus_connection`), e `independence` entre `adapters.inbound` y `adapters.outbound`.
Las raíces de composición (`__init__.py` y `config_flow.py` del paquete) quedan fuera de
los contratos: son los únicos módulos que conectan `adapters.inbound` con
`adapters.outbound`.

### 3.3 Modelo de dominio

```python
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
    key: str                          # también translation_key y sufijo del unique_id
    role: Role
    platform: Platform
    register: RegisterSpec
    poll: PollTier
    device_class: str | None = None   # cadenas: domain no importa HA
    state_class: str | None = None
    unit: str | None = None
    enum: Mapping[int, str] | None = None
    entity_category: str | None = None
    enabled_default: bool = True

@dataclass(frozen=True, kw_only=True)
class DeviceProfile:
    id: str                           # "ingeteam.oneplay_storage"
    brand: str
    device_type: str
    models: tuple[str, ...]
    min_request_interval_s: float
    default_port: int
    default_unit_id: int
    probe_key: str                    # entidad de prueba del config flow ("inverter_state", 0x101D)
    entities: tuple[EntitySpec, ...]
```

`validate_profile` comprueba: claves únicas, `probe_key` presente entre las claves del
perfil, rangos de registro sin solaparse, `enum` solo con `device_class == "enum"`,
`scale != 0`, tamaño de `dtype` coherente con `word_order`.

### 3.4 Puerto

```python
class DeviceGateway(Protocol):
    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[int, tuple[int, ...]]:
        """Palabras crudas por dirección. Lanza DeviceUnavailable o DeviceProtocolError."""
```

### 3.5 Aplicación

`read_tier(tier, gateway, profile) -> TierResult` es una función pura sobre el puerto:
1. Filtra las `EntitySpec` del tier.
2. Llama una vez a `gateway.read(...)` con sus `RegisterSpec`.
3. Decodifica cada una con `domain.decode`. Un `DecodeError` deja esa clave a `None` y
   anota el error; no aborta el tier.

`TierResult` contiene `values: dict[key, value | None]`, `raw: dict[key, tuple[int, ...]]`
y `decode_errors: dict[key, str]`.

`async probe_device(gateway: DeviceGateway, profile: DeviceProfile) -> None`
(`application/probe.py`) lee la entidad `profile.probe_key` y la decodifica. Propaga
`DeviceUnavailable` y `DeviceProtocolError` del gateway, y `DecodeError` si el valor no
es válido (por ejemplo, fuera del `enum`). La usa el config flow para validar el equipo.

### 3.6 Gateway saliente

`ModbusGateway(unit: ModbusUnit)`:
- Agrupa las direcciones contiguas en bloques (hueco máximo configurable, 0 por defecto) y
  lanza una lectura `read_holding_registers` / `read_input_registers` por bloque.
- Traduce excepciones: `ModbusConnectionError` y `ModbusTimeoutError` a
  `DeviceUnavailable`; `ModbusExceptionError` y `ModbusProtocolError` a
  `DeviceProtocolError`.
- **No** espacia peticiones por su cuenta: al crearse llama a
  `unit.set_message_spacing(profile.min_request_interval_s)`, que la librería aplica por
  unit en la conexión compartida.

## 4. Config flow y flujo de datos

### 4.1 Entry de marca (hub)

- Paso `user`: elegir la marca entre las del catálogo. En esta spec solo está `ingeteam`.
- `unique_id = brand`; si existe, aborta con `already_configured`.
- `data = {"brand": "ingeteam"}`; sin datos de conexión.
- `async_get_supported_subentry_types` (`config_entries.py:3068`) devuelve `{"device": DeviceSubentryFlow}`.

### 4.2 Subentry `device` (un equipo)

- Paso `user`, campos: `name`, `host`, `port` (por defecto `profile.default_port`),
  `unit_id` (por defecto `profile.default_unit_id`), `profile` (catálogo filtrado por la
  marca de la entry).
- Validación: el flow recibe del `config_flow.py` raíz una `gateway_factory`. Esta abre
  `async with async_get_temporary_unit(hass, ModbusTcpParams(host=..., port=...), unit_id)`
  y entrega un `ModbusGateway` sobre esa unit. El flow llama a
  `application.probe_device(gateway, profile)`, que lee `profile.probe_key`
  (`inverter_state`, `0x101D` en Ingeteam). El flow solo ve errores de dominio y el
  `HomeAssistantError` de la apertura:

  | Fallo | Error del formulario |
  |---|---|
  | `DeviceUnavailable` | `cannot_connect` |
  | `DeviceProtocolError`, `DecodeError` (valor fuera del `enum`) | `invalid_response` |
  | `HomeAssistantError` de `async_get_temporary_unit`: endpoint en uso con otros parámetros de enlace (`connection.py:62-65`) | `endpoint_in_use` |

- `unique_id = f"{host}:{port}:{unit_id}"` (host en minúsculas); si se repite en la
  entry, aborta con `already_configured`.
- `data = {host, port, unit_id, profile, intervals: {fast: 5, normal: 60, slow: 3600}}`.
- Paso `reconfigure`: cambia `host`, `port` e `intervals`. Cada intervalo ≥
  `profile.min_request_interval_s`. Recalcula el `unique_id` con el nuevo `host` y
  `port`; si choca con otra subentry de la misma entry, aborta con `already_configured`.
  Guarda con `async_update_and_abort(entry, subentry, unique_id=..., title=..., data_updates=...)`
  (`config_entries.py:3814-3822`). No hay options flow, porque las subentries no tienen
  `options`.

### 4.3 Ciclo de vida

- **Setup de la entry:** por cada subentry `device` crea un `DeviceRuntime` con su
  `ModbusUnit` (vía `async_get_unit(hass, entry, params, unit_id)`), un `ModbusGateway` y
  un `TierCoordinator` por tier que tenga entidades. Se guarda en
  `entry.runtime_data: dict[subentry_id, DeviceRuntime]`.
- **Cambios en subentries** (alta, baja, reconfigure): un update listener recarga la entry
  de marca. Es necesario porque `async_get_unit` ata la liberación de la unit a la entry
  (`connection.py:98`), no a la subentry: solo recargando la entry se cierra el socket de
  un equipo eliminado.
- **Unload:** descarga plataformas; HA libera las units y cierra cada conexión con su
  último consumidor.

### 4.4 Flujo de datos

```
TierCoordinator(tier).update_interval = intervals[tier]
  └─ _async_update_data()
       └─ application.read_tier(tier, gateway, profile)
            └─ ModbusGateway.read(specs) ─► ModbusUnit.read_holding_registers (por bloque)
            └─ domain.decode(spec, words)
       ◄─ TierResult (values, raw, decode_errors)
ModbusSolarEntity(CoordinatorEntity).native_value = result.values[key]
```

- Coordinators con `always_update=False`: HA solo escribe estado si el valor cambia.
- Identificadores estables: device `(DOMAIN, subentry_id)`; entity
  `unique_id = f"{subentry_id}_{key}"`. Se basan en el `subentry_id` (ULID) para que
  cambiar el host en reconfigure no duplique entidades.
- Dispositivo de marca `(DOMAIN, entry_id)`; cada equipo cuelga de él con `via_device`.
- Entidades añadidas con `async_add_entities(..., config_subentry_id=subentry_id)`.
- Nombres de entidad por `translation_key = key` y `has_entity_name = True`; textos en
  `strings.json` y `translations/{es,en}.json`, incluidos los estados del enum.

## 5. Errores y disponibilidad

- `domain/errors.py`: `DeviceUnavailable`, `DeviceProtocolError`, `DecodeError`. Solo el
  gateway conoce las excepciones de `modbus_connection`.
- En el coordinator, `DeviceUnavailable` y `DeviceProtocolError` → `UpdateFailed`: las
  entidades del tier pasan a `unavailable`.
- Un tier es todo o nada: si falla un bloque, falla el tier.
- `DecodeError` afecta a una entidad: su valor es `None` (`unknown`) y se registra un
  `warning` una vez por clave hasta que se recupere.
- Log según la quality scale: un `warning` al perder el equipo y un `info` al recuperarlo;
  nada en cada tick.
- Arranque: un equipo caído **no** bloquea la entry de marca. No se lanza
  `ConfigEntryNotReady`. Cada coordinator hace `async_refresh()`; las entidades nacen
  `unavailable` y se recuperan en el siguiente tick.
- Si otro cliente ocupa el único puerto Modbus del Ingeteam (por ejemplo, el EMS), se ve
  como `DeviceUnavailable`. Se documenta en `docs/guides/setup.md`. Sin reintento
  agresivo: se reintenta en el siguiente tick.

## 6. Diagnostics

`async_get_device_diagnostics` (en el dispositivo de cada equipo) devuelve:
- `profile.id` e `intervals`;
- por tier: `last_update_success`, último error y su hora;
- por entidad: `address`, `dtype`, `word_order`, `scale`, `raw` (palabras) y valor
  decodificado.

`async_get_config_entry_diagnostics` agrega lo mismo para todos los equipos de la marca.
`host` se oculta con `async_redact_data`. El coordinator conserva el último `TierResult`
completo para alimentarlo.

Uso: verificar en la VM los supuestos de escala y `word_order` del §2.

## 7. Tests, calidad y CI

**Todos los tests se ejecutan solo en GitHub Actions; nunca en la máquina Windows.**

### 7.1 Tests

Las dos carpetas son organización, no entornos distintos: ambas corren en el mismo job
`test` (§7.3) con HA instalado, porque importar `custom_components.modbus_solar.<capa>`
ejecuta antes `custom_components/modbus_solar/__init__.py`, que importa `homeassistant`.

`tests/unit/` (sin fixture `hass`; lógica pura de domain, application, profiles y gateway):
- `decode`: u16, s16, u32, s32, ambos `word_order`, `scale`, `offset`, `enum`, valor fuera
  del enum.
- `validate_profile`: cada regla del §3.3, y que el perfil Ingeteam pasa.
- `read_tier` con un `DeviceGateway` falso: éxito, error del gateway, `DecodeError`
  parcial.
- `ModbusGateway` con `mock_modbus_unit`: agrupado en bloques, traducción de cada
  excepción (`fail_read`), y que llama a `set_message_spacing`.
- Formatos de `unique_id` estables (patrón de `irrigation-scheduler`,
  `entities/tests/test_entities.py:7-11`).

`tests/ha/` (con fixture `hass` de `pytest-homeassistant-custom-component`):
- Flow de marca: alta y duplicado.
- Subentry: alta OK, `cannot_connect`, `endpoint_in_use`, `invalid_response`, duplicado,
  reconfigure con intervalo inferior al mínimo.
- Setup/unload de la entry; recarga al cambiar subentries.
- Entidades: valores, `unavailable` con equipo caído y recuperación.
- Diagnostics con `host` oculto.
- Se parchea `async_get_unit` / `async_get_temporary_unit` para devolver `MockModbusUnit`.
- `conftest.py` con el fixture autouse `auto_enable_custom_integrations`, como en
  `irrigation-scheduler` (`engine/tests/conftest.py:24-26`).

### 7.2 Configuración (`pyproject.toml`)

Basada en `irrigation-scheduler/pyproject.toml:1-12`:
- ruff: `target-version = "py314"`, `line-length = 120`, `select = ["E", "F", "I", "UP", "B"]`.
- pytest: `testpaths = ["tests"]` (no dentro del paquete), `pythonpath = ["."]`,
  `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"`.
- `[tool.importlinter]` con los contratos del §3.2.

### 7.3 Workflows

Basados en `irrigation-scheduler/.github/workflows/tests.yml:1-23` (Ubuntu, Python 3.14,
`pytest-homeassistant-custom-component==0.13.367`, ruff, `compileall`, pytest).

`tests.yml`, con `on: push` a `main`, `feat/**`, `fix/**`, `refactor/**`, `docs/**`, y
`pull_request`:

| Job | Pasos |
|---|---|
| `lint` | instala `ruff` e `import-linter`; `ruff check .`, `ruff format --check .`, `lint-imports`, `python -m compileall -q custom_components` |
| `test` | instala `pytest-homeassistant-custom-component==0.13.367`, `pymodbus==3.13.1`, `modbus-connection[tmodbus]==4.10.0` y `tmodbus==0.6.2`; `pytest` (recorre `tests/unit` y `tests/ha`) |

Dependencias del job `test`, verificadas en PyPI y en el core:
- `pytest-homeassistant-custom-component==0.13.367` fija `homeassistant==2026.9.4`
  (metadatos `requires_dist`, https://pypi.org/pypi/pytest-homeassistant-custom-component/0.13.367/json).
  Cumple el mínimo 2026.9.0 de `hacs.json`.
- `homeassistant==2026.9.4` no arrastra `modbus-connection` (ningún `requires_dist` contiene
  `modbus`, https://pypi.org/pypi/homeassistant/2026.9.4/json). Los requisitos de una
  integración del core no se instalan con el paquete; por eso el job instala a mano los tres
  pines del manifest de `modbus` (HA 2026.9.4 `homeassistant/components/modbus/manifest.json:8-11`).
  Sin ellos, `homeassistant/components/modbus/connection.py:9-16` no importa y el mock de
  `modbus_connection` no existe.

`validate.yml` (push y pull_request), dos jobs:
- `hassfest`: `home-assistant/actions/hassfest`. Valida el manifest con
  `CUSTOM_INTEGRATION_MANIFEST_SCHEMA` (core `script/hassfest/manifest.py`, commit
  `743b1489`): `domain`, `name`, `documentation` (https y fuera de `home-assistant.io`) y
  `codeowners` obligatorios (`:207-208`, `:309`, `:151-161`, `:350-352`); `version` obligatorio
  en custom integrations (`:360-366`, `:422-423`) y con formato válido (`:180-194`); `iot_class`
  obligatorio (`:393-398`); `domain` igual al nombre de la carpeta (`:382-383`); claves en orden
  `domain`, `name` y resto alfabético (`:426-447`).
- `hacs`: `hacs/action` con `category: integration` e `ignore: license`. Checks que aplican a
  una integración (hacs/integration `custom_components/hacs/validate/`, commit `4b64080f`;
  lista en https://hacs.xyz/docs/publish/action/):

| Check | Cómo se satisface |
|---|---|
| `archived` | repositorio no archivado (`archived.py`) |
| `brands` | `custom_components/modbus_solar/brand/icon.png` en el repo; el check lo busca en `<ruta del contenido>/brand/icon.png` antes de consultar home-assistant/brands (`brands.py`). Ver §8 |
| `description` | descripción del repositorio en GitHub (`description.py`); ajuste del repo, no fichero |
| `hacsjson` | `hacs.json` del §8; con `zip_release: true` exige `filename` (`hacsjson.py`) |
| `information` | `README.md` en la raíz (`information.py`) |
| `integration_manifest` | manifest con `codeowners`, `documentation`, `domain`, `issue_tracker`, `name` y `version` (`utils/validate.py`, `INTEGRATION_MANIFEST_JSON_SCHEMA`) |
| `issues` | issues habilitadas en el repositorio (`issues.py`) |
| `topics` | al menos un topic en el repositorio (`topics.py`) |
| `license` | **ignorado**. Exige licencia aprobada por OSI (`license.py`); el repo usa PolyForm Noncommercial 1.0.0 (`LICENSE:3`), que no lo es. La licencia es una decisión del proyecto |
| `images` | no aplica: solo `plugin` y `theme` (`images.py`) |

`description`, `issues` y `topics` son ajustes del repositorio `sigergy/modbus-solar-inverter`
en GitHub; el plan los incluye como tarea manual previa al primer push de `validate.yml`.

`release.yml` (tag `v*.*.*`): comprueba que `version` del manifest coincide con el tag,
empaqueta `custom_components/modbus_solar` en `modbus_solar.zip` y lo adjunta a la release de
GitHub.

## 8. Empaquetado HACS

- `hacs.json`: `{"name": "Modbus Solar", "zip_release": true, "filename": "modbus_solar.zip", "homeassistant": "2026.9.0"}`.
  Todas las claves están en `HACS_MANIFEST_JSON_SCHEMA` (hacs/integration
  `custom_components/hacs/utils/validate.py`, commit `4b64080f`).
- `manifest.json` (claves en el orden que exige hassfest; requisitos en §7.3):

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

  `requirements: []` porque usa los del core `modbus`. `version` coincide con el tag de la
  release (`release.yml`, §7.3). Mismo patrón que
  `irrigation-scheduler/custom_components/irrigation_scheduler/manifest.json`.
- Brand: `custom_components/modbus_solar/brand/icon.png` dentro del paquete, sin PR a
  home-assistant/brands. Desde HA 2026.3 una custom integration sirve sus imágenes desde
  `brand/` y tienen prioridad sobre el repositorio de brands
  (https://developers.home-assistant.io/docs/core/integration/brand_images, sección «Custom
  integrations»; código en HA 2026.9.0 `homeassistant/components/brands/__init__.py:136-156`
  y `homeassistant/loader.py:898-900`). HACS lo acepta en el check `brands` (§7.3) y lo pide
  en https://hacs.xyz/docs/publish/integration/ («Brand assets»). Nombres admitidos:
  `icon.png`, `logo.png`, variantes `@2x` y `dark_` (`brands/const.py`, `ALLOWED_IMAGES`).
  Punto a verificar en el plan: tamaño y formato exigidos para `icon.png` (las fuentes leídas
  no los fijan).
- Sin frontend en esta spec.

## 9. Documentación

```
docs/
  README.md                                índice y estado de los cambios
  architecture/overview.md                 capas, reglas de dependencia, flujo de datos
  architecture/{domain,application,ports}.md
  architecture/adapters/{inbound,outbound}.md
  decisions/0001..0008-*.md                ADR (abajo)
  changes/2026-10-04-skeleton/spec.md      esta spec (+ plan.md)
  research/architecture-analysis.md        análisis previo (movido desde brainstorming/)
  guides/{setup,testing,release}.md
  features/{device-setup,monitoring}.md   docs funcionales vivas (tarea de cierre)
  wiki/brands/ingeteam/
    README.md                              fuentes, revisión, SHA-256, fecha de obtención
    AAA0030IMB03_N.pdf                     comandos, genérico de marca (rev. N, 20/05/24)
    1-play-tl-m/
      ACL2010IMB05.pdf                     input registers 1Play Storage
      registers.md                         tabla extraída, con página por fila
```

PDF oficiales y públicos (no oficiales no entran en el repo):

| Documento | SHA-256 |
|---|---|
| `Input_REG_Modbus_1P-Storage-ACL2010IMB05_.pdf` | `c0e6533edbd194974aba3e9fc3f040a65e009cabdd143aea6a02e6b2578620d4` |
| `Write_REG_Modbus_1P-Storage-AAA0030IMB03_.pdf` (rev. N) | `b53eb0c3ad36230365833a798429e1e0d3be3ed8488e361fb70ceb1ee4c1d332` |

La revisión F de AAA0030IMB03 (09/02/18), encontrada en `OneDrive/Documentos/SharedAsLink`,
es anterior y se descarta. `ACL0000IMC01` (estados y eventos) sigue sin conseguirse.

ADR (un fichero por decisión):
1. `0001-hexagonal-import-linter.md`: hexagonal estricto verificado con import-linter.
2. `0002-python-profiles.md`: perfiles en Python; SunSpec por escaneo en spec 3;
   export/import JSON en la última fase.
3. `0003-modbus-shared-connection.md`: conexión vía `modbus.async_get_unit` y
   `modbus-connection`; sin pymodbus directo.
4. `0004-entry-brand-subentry-device.md`: entry = marca, subentry = equipo.
5. `0005-poll-tiers.md`: tiers 5/60/3600 s editables en reconfigure, mínimo del perfil.
6. `0006-vendor-docs-official-only.md`: solo PDF oficiales en el repo.
7. `0007-tests-ci-only.md`: tests solo en GitHub Actions.
8. `0008-license-polyform-noncommercial.md`: PolyForm Noncommercial 1.0.0 con `Required Notice`;
   se puede relajar a AGPL-3.0 más adelante, pero no endurecer (las versiones publicadas
   conservan su licencia). Por eso `hacs/action` ignora el check `license`.

**Tarea de cierre (paso 4 del flujo de `docs/`).** Al terminar la implementación, antes de
marcar esta spec como `status: done`:
- `features/device-setup.md`: alta de la marca y del equipo, campos del formulario,
  errores (`cannot_connect`, `endpoint_in_use`, `invalid_response`), reconfigure e
  intervalos.
- `features/monitoring.md`: los 3 sensores con su unidad y tier, disponibilidad,
  recuperación, uso en el panel de Energía y diagnostics.
- `architecture/` y `guides/` reflejan el código final.
- `README.md` marca este cambio como cerrado.

Flujo de `docs/`: `research/` → `decisions/` → `changes/` → al cerrar, `features/`,
`architecture/` y `guides/`. `wiki/` es la fuente de datos de fabricantes.

## 10. Riesgos y pendientes

| Riesgo / pendiente | Mitigación |
|---|---|
| Escala `[X x 10]` y `word_order` sin verificar | diagnostics muestra raw y valor; verificación en la VM antes de spec 1 |
| Un único cliente Modbus en el Ingeteam | documentado; si el EMS ocupa el puerto, el equipo sale `unavailable` |
| Falta `ACL0000IMC01` (eventos) | eventos fuera de spec 0; se piden a Ingeteam |
| Recargar la entry de marca reinicia todos sus equipos | aceptable: las altas y bajas de equipos son raras |
| El pin de `pytest-homeassistant-custom-component` puede no casar con HA 2026.9 | se verifica en el plan |
