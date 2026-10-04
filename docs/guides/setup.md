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

## Clientes Modbus en el Ingeteam

Ingeteam recomienda un único cliente conectado al puerto 502 del 1Play Storage y un periodo entre peticiones de al menos 1 s (`docs/wiki/brands/ingeteam/1-play-tl-m/ACL2010IMB05.pdf`, pág. 4). Su guía genérica de comunicaciones dice que los INGECON SUN admiten conexiones simultáneas de varios clientes en el puerto 502, sin prioridad entre peticiones (`docs/wiki/brands/ingeteam/AAX2023IPD02_E.pdf`, pág. 7). Qué pasa en el 1Play con un segundo cliente, por ejemplo el EMS, no está verificado: se comprueba en la VM.

Si una lectura falla por la conexión, se traduce a `DeviceUnavailable` (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:36-37`). El `TierCoordinator` la convierte en `UpdateFailed` y el equipo sale `unavailable` (`custom_components/modbus_solar/adapters/inbound/coordinator.py:54-58`).

No hay reintento agresivo: se reintenta en el siguiente tick del tier (spec §5, `docs/changes/2026-10-04-skeleton/spec.md:353-355`). Cuando la lectura vuelve a funcionar, el equipo se recupera solo. El perfil espacia las peticiones 1 s, como recomienda Ingeteam (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:11-12`).
