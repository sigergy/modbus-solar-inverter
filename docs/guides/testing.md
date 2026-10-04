# Guía: tests

Los tests solo corren en GitHub Actions ([ADR 0007](../decisions/0007-tests-ci-only.md)). Nunca `pytest` en la máquina Windows.

## `tests/unit` frente a `tests/ha`

| Carpeta | Qué prueba | Necesita HA |
|---|---|---|
| `tests/unit/` | `domain`, `application`, `profiles`, `ModbusGateway`, empaquetado y traducciones | no |
| `tests/ha/` | coordinators, setup, sensores, config flow y diagnostics | sí (`hass`) |

- `tests/unit/` importa `custom_components.modbus_solar.…` y usa `FakeGateway` o el mock de `modbus_connection` (`tests/unit/test_modbus_gateway.py:1-14`).
- `tests/ha/` carga la integración con `enable_custom_integrations`, activado en cada test (`tests/ha/conftest.py:12-14`).
- La configuración de pytest está en `pyproject.toml:14-18`.

## Fixtures de `tests/ha/conftest.py`

| Fixture | Qué hace | Cita |
|---|---|---|
| `ingeteam_unit` | `MockModbusUnit` con los tres registros del Ingeteam: `0x101D`, `0x1021` y `0x1037` | `tests/ha/conftest.py:17-22` |
| `temp_unit` | sustituye `async_get_temporary_unit` del config flow por `ingeteam_unit` | `tests/ha/conftest.py:25-34` |
| `patch_unit` | sustituye `async_get_unit` del setup por `ingeteam_unit` | `tests/ha/conftest.py:37-41` |

Los parches apuntan a los nombres importados en la raíz: `custom_components.modbus_solar.config_flow.async_get_temporary_unit` y `custom_components.modbus_solar.async_get_unit` (`tests/ha/conftest.py:33`, `:40`).

## `FakeGateway`

`tests/fakes.py:11-23`: `DeviceGateway` en memoria. Devuelve `words[address]` por cada `RegisterSpec` o lanza el `error` que se le pase. Guarda las llamadas en `calls`. `INGETEAM_WORDS` (`tests/fakes.py:8`) lleva los mismos valores que `ingeteam_unit`: `grid_connected`, 5000,0 Wh y 1234,5 W.

Se usa en `tests/unit/test_poller.py`, `tests/unit/test_probe.py` y `tests/ha/test_coordinator.py`. El resto de `tests/ha/` usa `ingeteam_unit` con el gateway real.

## Ciclo RED / GREEN

1. `bash scripts/lint.sh`.
2. Commit `test(red): …` con el test que falla.
3. `bash scripts/ci-wait.sh`: empuja `HEAD`, espera el run de `tests.yml` y espera rojo. Si falla, imprime el log de los pasos fallidos (`scripts/ci-wait.sh:2-6`, `:17`).
4. Implementación.
5. `bash scripts/lint.sh`.
6. Commit GREEN.
7. `bash scripts/ci-wait.sh` debe salir con `exit 0` (`scripts/ci-wait.sh:18-19`).

`bash scripts/ci-wait.sh validate.yml` espera el workflow `validate` (hassfest y HACS) en lugar de `tests.yml` (`scripts/ci-wait.sh:5`). Cada ciclo cuesta minutos de CI.

## Pines del job `test`

Copiados de `.github/workflows/tests.yml:36-41`:

| Paquete | Versión |
|---|---|
| `pytest-homeassistant-custom-component` | `0.13.367` |
| `pymodbus` | `3.13.1` |
| `modbus-connection[tmodbus]` | `4.10.0` |
| `tmodbus` | `0.6.2` |

Python 3.14 (`.github/workflows/tests.yml:34`). Los tres últimos coinciden con el manifest de `modbus` de HA 2026.9 (`docs/changes/2026-10-04-skeleton/spec.md:54`). Si cambia la versión mínima de HA, se revisan juntos.
