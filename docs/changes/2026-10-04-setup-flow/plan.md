---
type: feature
area: config-flow
layers: [application, adapters]
status: done
date: 2026-10-04
---

# Plan de implementación — Spec 2, flujo de alta con una entry por inversor

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `subagent-driven-development` (recomendada) o
> `executing-plans` para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** sustituir la entry de marca con subentries por una entry por inversor, con un
alta en tres pasos (modelo → conexión → confirmación con lecturas), según
`docs/changes/2026-10-04-setup-flow/spec.md`.

**Arquitectura:** `probe_device` pasa a devolver las lecturas del tier `fast`. El flow vive en
`adapters/inbound/flow.py` y recibe catálogo y gateway por inyección desde `config_flow.py`. El
runtime pasa de un dict por subentry a un único `DeviceRuntime` por entry, con `entry_id` donde
antes iba `subentry_id`.

**Stack:** Python 3.14, Home Assistant 2026.9.4, `modbus-connection` 4.10.0, pytest +
`pytest-homeassistant-custom-component` 0.13.367, ruff, import-linter, GitHub Actions.

## Global Constraints

- Rama de trabajo: `feat/setup-flow`, creada desde `main`. Nunca commit en `main`.
- Push a `feat/setup-flow` autorizado sin confirmar. Force push, merge, rebase y PR piden
  confirmación.
- **Tests solo en GitHub Actions.** Nunca `pytest` en la máquina Windows. RED y GREEN se
  comprueban con `bash scripts/ci-wait.sh`, lanzado con `run_in_background: true`.
- Gates locales antes de cada commit: `bash scripts/lint.sh`. `.venv/` no se commitea.
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
- Identificadores estables: entidad `f"{entry_id}_{key}"`; entry
  `f"{host.lower()}:{port}:{unit_id}"`.
- `PROBE_TIMEOUT_S = 20`.
- `graft/` y `.graft_*` nunca se commitean.
- No inventar: si una API no se comporta como dice el plan, parar y avisar con la salida real.

## Mapa de ficheros

Rutas de código relativas a `custom_components/modbus_solar/`.

| Fichero | Cambio | Tarea |
|---|---|---|
| `application/probe.py` | devuelve `TierResult` del tier `fast` | 1 |
| `adapters/inbound/flow.py` | reescrito: `DeviceConfigFlow`, `format_readings`, `PROBE_TIMEOUT_S` | 2 |
| `config_flow.py` | compone `DeviceConfigFlow` | 2 |
| `__init__.py` | un runtime por entry, sin listener, `async_migrate_entry` | 2 |
| `const.py` | sin `CONF_BRAND` ni `SUBENTRY_DEVICE` | 2 |
| `adapters/inbound/runtime.py` | `entry_id`, `ConfigEntry[DeviceRuntime]` | 2 |
| `adapters/inbound/entities/{base,factory,energy}.py` | sin `brand_device_id` | 2 |
| `sensor.py`, `diagnostics.py`, `adapters/inbound/diagnostics.py` | un equipo por entry | 2 |
| `manifest.json` | `integration_type: device` | 2 |
| `strings.json`, `translations/en.json`, `translations/es.json` | pasos del flow nuevo | 2 |
| `tests/…` | ver cada tarea | 1, 2 |
| ADR 0010, `docs/…`, `README.md` | documentación | 3 |

---

### Tarea 1: la sonda devuelve lecturas

**Files:**
- Modify: `application/probe.py`
- Test: `tests/unit/test_probe.py`

**Interfaces:**
- Produces: `probe_device(gateway, profile) -> TierResult`.

- [ ] **Step 1: tests que fallan.** En `tests/unit/test_probe.py`, sustituir
  `test_reads_only_the_probe_register` por:

```python
async def test_reads_probe_register_then_fast_tier() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    await probe_device(gateway, ONEPLAY)
    assert [[spec.address for spec in call] for call in gateway.calls] == [[0x101D], [0x101D, 0x1037]]


async def test_returns_fast_readings() -> None:
    result = await probe_device(FakeGateway(INGETEAM_WORDS), ONEPLAY)
    assert result.values == {"inverter_state": "grid_connected", "active_power": 1234.5}


async def test_entities_disabled_by_default_are_not_read() -> None:
    entities = tuple(replace(e, enabled_default=e.key != "active_power") for e in ONEPLAY.entities)
    result = await probe_device(FakeGateway(INGETEAM_WORDS), replace(ONEPLAY, entities=entities))
    assert result.values == {"inverter_state": "grid_connected"}
```

(con `from dataclasses import replace`).

- [ ] **Step 2:** `bash scripts/lint.sh`, commit `test(red): probe returns fast readings`,
  push, `bash scripts/ci-wait.sh` → rojo (`probe_device` devuelve `None`).

- [ ] **Step 3: implementación.** `application/probe.py`:

```python
"""Validación de un equipo nuevo: entidad de prueba y lecturas del tier fast."""

from ..domain.decode import decode
from ..domain.profile import DeviceProfile
from ..domain.types import PollTier
from ..ports.device import DeviceGateway
from .poller import TierResult, read_tier


async def probe_device(gateway: DeviceGateway, profile: DeviceProfile) -> TierResult:
    spec = next(e for e in profile.entities if e.key == profile.probe_key)
    words = await gateway.read([spec.register])
    # DecodeError si el valor no es válido (por ejemplo, fuera del enum)
    decode(spec, words[spec.register])
    # lecturas que muestra el paso de confirmación del config flow
    keys = {e.key for e in profile.entities if e.enabled_default}
    return await read_tier(PollTier.FAST, gateway, profile, keys)
```

- [ ] **Step 4:** lint, commit `feat: probe returns fast tier readings`, push, CI verde.

---

### Tarea 2: una entry por inversor

Las piezas van acopladas (el tipo de `runtime_data` cambia en todas): un único RED y un único
GREEN.

**Files:**
- Modify: todos los de la tarea 2 del mapa.
- Delete: `tests/ha/test_subentry_flow.py`.
- Test: `tests/ha/common.py`, `tests/ha/test_config_flow.py` (reescrito), `tests/ha/test_init.py`,
  `tests/ha/test_sensor.py`, `tests/ha/test_diagnostics.py`, `tests/ha/test_coordinator.py`,
  `tests/ha/test_energy.py`, `tests/unit/test_readings.py` (nuevo),
  `tests/unit/test_translations.py`, `tests/unit/test_packaging.py`.

**Interfaces:**
- Consumes: `probe_device(gateway, profile) -> TierResult` (tarea 1).
- Produces:
  - `DeviceConfigFlow(ConfigFlow)`, `VERSION = 2`, ClassVar `catalog: Catalog` y
    `gateway_factory: GatewayFactory`; pasos `user`, `connection`, `confirm`, `reconfigure`.
  - `format_readings(profile, result, translations) -> str`.
  - `DeviceRuntime(entry_id, title, profile, intervals, gateway, coordinators)`.
  - `ModbusSolarConfigEntry = ConfigEntry[DeviceRuntime]`.
  - `entity_unique_id(entry_id, key)`, `enabled_keys(registry, entry_id, profile)`,
    `build_runtime(hass, entry, profile, gateway, keys)`.
  - `build_sensors(runtime)`; `ModbusSolarEntity(coordinator, runtime, spec)`.
  - `device_diagnostics(runtime, entry_data)` con la clave `entry`.

- [ ] **Step 1: tests que fallan.**

`tests/ha/common.py`: sustituir `DEVICE` y `brand_entry` por:

```python
def device_entry(
    data: dict[str, Any] = DEVICE_DATA, entry_id: str = DEVICE_ID, title: str = "Inverter"
) -> MockConfigEntry:
    """Entry v2 de un inversor."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        entry_id=entry_id,
        title=title,
        data=dict(data),
        unique_id=f"{data['host']}:{data['port']}:{data['unit_id']}",
    )
```

y `entity_id_of(hass, key, entry_id=DEVICE_ID)`.

`tests/ha/test_config_flow.py`, reescrito. Fixture autouse que parchea
`custom_components.modbus_solar.async_setup_entry` (`return_value=True`). Casos:

| Test | Comprueba |
|---|---|
| `test_model_step_lists_every_profile` | opciones `Ingeteam · 1Play TL M` y `Ingeteam · STORAGE 1Play TL M`, modo `list` |
| `test_connection_defaults_come_from_profile` | sección `advanced` plegada con `port` 502 y `unit_id` 1 |
| `test_add_inverter` | `confirm` con host y lecturas `- Inverter state: Connected to grid\n- Active power: 1234.5 W`; entry v2 con título, `unique_id` `inverter.lan:502:1` y `data`; unit temporal con `ModbusTcpParams(host="Inverter.LAN", port=502)` |
| `test_name_defaults_to_brand_and_model` | `Ingeteam 1Play TL M` |
| `test_duplicate_aborts_before_probing` | `already_configured` sin abrir unit |
| `test_probe_errors_show_form_error` | `cannot_connect`, `invalid_response` (×2), `endpoint_in_use`; sin entries |
| `test_probe_timeout_is_cannot_connect` | unit que no responde con `PROBE_TIMEOUT_S` parcheado a 0,01 |
| `test_form_recovers_after_error` | tras `cannot_connect`, reenviar llega a `confirm` |
| `test_reconfigure_updates_host_port_and_intervals` | `reconfigure_successful`, `unique_id` y `data` nuevos |
| `test_reconfigure_rejects_interval_shorter_than_blocks` | `{"fast": "interval_too_short"}` |
| `test_reconfigure_aborts_if_endpoint_belongs_to_other_device` | `already_configured` |
| `test_reconfigure_keeps_own_endpoint` | `reconfigure_successful` |

`tests/ha/test_init.py`:

| Test | Comprueba |
|---|---|
| `test_setup_builds_runtime_and_device` | `runtime_data.entry_id`, `async_get_unit` con la entry y el endpoint, un solo dispositivo `(DOMAIN, DEVICE_ID)` sin `via_device_id` |
| `test_unload` | `NOT_LOADED` |
| `test_v1_entry_is_not_migrated` | entry v1 → `MIGRATION_ERROR` y el mensaje de la spec §6 en el log |
| `test_reconfigure_reloads_with_new_endpoint` | tras el reconfigure la entry vuelve a `LOADED` y abre la unit con el endpoint nuevo |

`tests/ha/test_sensor.py`, `test_diagnostics.py`, `test_coordinator.py`, `test_energy.py`:
`brand_entry(DEVICE)` → `device_entry()`; `brand_entry(STORAGE)` → `device_entry(STORAGE)` con
`STORAGE = {**DEVICE_DATA, "profile": "ingeteam.oneplay_storage"}`; sin `config_subentry_id`;
`build_runtime(hass, entry, profile, gateway, keys)`; `runtime.entry_id`. Diagnostics de la
entry sin el nivel `devices`, clave `entry`; el del dispositivo igual al de la entry.

`tests/unit/test_readings.py` (nuevo): `format_readings` con nombre y estado traducidos,
unidad, `—` para `None` y la clave cuando falta la traducción.

`tests/unit/test_translations.py`: pasos `{user, connection, confirm, reconfigure}`, errores y
aborts en `config`, sin `config_subentries`.

`tests/unit/test_packaging.py`: `integration_type == "device"`.

- [ ] **Step 2:** borrar `tests/ha/test_subentry_flow.py`, lint, commit
  `test(red): one config entry per inverter`, push, CI rojo.

- [ ] **Step 3: implementación.**

`adapters/inbound/flow.py`, reescrito:

```python
PROBE_TIMEOUT_S = 20
CONF_ADVANCED = "advanced"


def format_readings(profile: DeviceProfile, result: TierResult, translations: Mapping[str, str]) -> str:
    """Lista markdown de las lecturas de la sonda, con nombres y estados traducidos."""
    prefix = f"component.{DOMAIN}.entity.sensor"
    lines: list[str] = []
    for spec in profile.entities:
        if spec.key not in result.values:
            continue
        value = result.values[spec.key]
        if value is None:
            text = "—"
        elif spec.enum is not None:
            text = translations.get(f"{prefix}.{spec.key}.state.{value}", str(value))
        else:
            text = f"{value} {spec.unit}" if spec.unit else str(value)
        lines.append(f"- {translations.get(f'{prefix}.{spec.key}.name', spec.key)}: {text}")
    return "\n".join(lines)


class DeviceConfigFlow(ConfigFlow):
    VERSION = 2
    catalog: ClassVar[Catalog]
    gateway_factory: ClassVar[GatewayFactory]

    async def async_step_user(self, user_input=None):
        # SelectSelector en modo list con una opción por perfil; al enviar guarda el perfil
        # y pasa a async_step_connection()

    async def async_step_connection(self, user_input=None):
        # host + section(advanced: port, unit_id; collapsed)
        # async_set_unique_id + _abort_if_unique_id_configured antes de la sonda
        # sonda dentro de asyncio.timeout(PROBE_TIMEOUT_S):
        #   EndpointInUse → endpoint_in_use; DeviceUnavailable, TimeoutError → cannot_connect;
        #   DeviceProtocolError, DecodeError → invalid_response
        # sin error: guarda conexión y lecturas formateadas; pasa a async_step_confirm()

    async def async_step_confirm(self, user_input=None):
        # name (por defecto "{marca} {primer modelo}"); placeholders host y readings
        # async_create_entry(title=name, data={host, port, unit_id, profile, intervals})

    async def async_step_reconfigure(self, user_input=None):
        # mismo formulario y validación que el reconfigure del subentry;
        # duplicado contra _async_current_entries(); async_update_reload_and_abort
```

`__init__.py`:

```python
async def async_setup_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    data = entry.data
    profile = CATALOG.get(data[CONF_PROFILE])
    # conexión compartida por endpoint; HA la libera al descargar la entry
    unit = async_get_unit(hass, entry, ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT]), data[CONF_UNIT_ID])
    gateway = ModbusGateway(unit, profile)
    keys = enabled_keys(er.async_get(hass), entry.entry_id, profile)
    entry.runtime_data = build_runtime(hass, entry, profile, gateway, keys)
    # primer refresh en segundo plano: un equipo caído no retrasa el arranque ni bloquea la entry
    for coordinator in entry.runtime_data.coordinators.values():
        entry.async_create_background_task(hass, coordinator.async_refresh(), f"{coordinator.name} first refresh")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ModbusSolarConfigEntry) -> bool:
    if entry.version == 1:
        # v1 = entry de marca con un subentry por equipo: no se migra (ADR 0010)
        _LOGGER.error("Modbus Solar now uses one entry per inverter instead of one per brand. "
                      "Delete this entry and add each inverter again.")
        return False
    return True
```

Resto: los cambios de la tabla §7 de la spec. `strings.json` con `config.step.user`,
`connection` (con `sections.advanced`), `confirm` (`{host}`, `{readings}`) y `reconfigure`;
`config.error` y `config.abort`. `en.json` copia literal; `es.json` mismas claves.

- [ ] **Step 4:** lint, commit `feat: one config entry per inverter with guided setup`, push, CI
  verde.

---

### Tarea 3: documentación

**Files:**
- Create: `docs/decisions/0010-entry-per-device.md`.
- Modify: `docs/decisions/0004-entry-brand-subentry-device.md` (solo el `status`:
  `superseded by 0010`), `docs/architecture/overview.md`, `docs/architecture/adapters/inbound.md`,
  `docs/architecture/application.md`, `docs/architecture/domain.md`,
  `docs/features/device-setup.md`, `docs/features/monitoring.md`, `docs/guides/setup.md`,
  `README.md`, `docs/README.md`.

- [ ] **Step 1:** ADR 0010 con contexto (problemas de la VM), decisión (spec §2-§6) y
  consecuencias (sin migración, una conexión por entry, sin agrupación por marca).
- [ ] **Step 2:** quitar toda mención a entry de marca, subentry y dispositivo de marca.
  Citas `archivo:línea` contra el código de la tarea 2.
- [ ] **Step 3:** `docs/README.md`: fila del cambio. `status: done` en spec y plan.
- [ ] **Step 4:** `grep -rn "subentr\|brand entry\|entry de marca" docs README.md` sin
  resultados fuera de ADR 0004 y de los cambios cerrados. Commit `docs: one entry per inverter`.
