# Guía: entorno de desarrollo

## Preparar el entorno

```bash
git clone https://github.com/sigergy/modbus-solar-inverter.git
cd modbus-solar-inverter
py -3.14 -m venv .venv
.venv/Scripts/python -m pip install ruff import-linter
bash scripts/lint.sh
```

`.venv/` no se commitea (`.gitignore:3`). `scripts/lint.sh` usa `.venv/Scripts` en Windows y `.venv/bin` en el resto (`scripts/lint.sh:7-8`).
`scripts/lint.sh` ejecuta, sin tests (`scripts/lint.sh:9-13`):

1. `ruff format .`
2. `ruff check .`
3. `lint-imports --config ../pyproject.toml`, desde `custom_components/`: contratos de capas ([overview](../architecture/overview.md)).
4. `python -m compileall -q custom_components tests`

## Por qué no hay pytest local

Los tests solo corren en GitHub Actions: la máquina de desarrollo es Windows y Home Assistant no se instala allí. Decisión: [ADR 0007](../decisions/0007-tests-ci-only.md). Ciclo y fixtures: [testing](testing.md).

## Un solo cliente Modbus en el Ingeteam

El Ingeteam 1Play Storage admite un único cliente Modbus en el puerto 502 (`docs/changes/2026-10-04-skeleton/spec.md:66`). Si otro cliente, por ejemplo el EMS, ocupa el puerto, la lectura falla como `DeviceUnavailable` (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:36-37`). El `TierCoordinator` la convierte en `UpdateFailed` y el equipo sale `unavailable` (`custom_components/modbus_solar/adapters/inbound/coordinator.py:54-58`).

No hay reintento agresivo: se reintenta en el siguiente tick del tier (spec §5, `docs/changes/2026-10-04-skeleton/spec.md:353-355`). Cuando el puerto queda libre, el equipo se recupera solo. El equipo exige además un periodo entre peticiones ≥ 1 s (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:11-12`).
