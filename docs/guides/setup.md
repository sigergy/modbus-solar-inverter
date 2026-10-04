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

En el STORAGE 1Play TL M, Ingeteam recomienda un único cliente conectado al puerto 502, al menos 1 s entre peticiones y no más de 10 registros por petición (`docs/wiki/brands/ingeteam/storage-1-play-tl-m/ABH2014IQM01.pdf`, apdo. 19.6.1, pág. 50). Con otro cliente conectado no garantiza las respuestas. El perfil aplica los dos límites (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:95-97`).

En el 1Play TL M sin storage, la recomendación es la misma: un único cliente y al menos 1 s entre peticiones (`docs/wiki/brands/ingeteam/1-play-tl-m/ACL2010IMB05.pdf`, pág. 4). Su guía genérica de comunicaciones dice que los INGECON SUN admiten conexiones simultáneas de varios clientes en el puerto 502, sin prioridad entre peticiones (`docs/wiki/brands/ingeteam/AAX2023IPD02_E.pdf`, pág. 7).

Qué pasa con un segundo cliente, por ejemplo el EMS, no está verificado: se comprueba en la VM.

Si una lectura falla por la conexión, se traduce a `DeviceUnavailable` (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:36-37`). El `TierCoordinator` la convierte en `UpdateFailed` y el equipo sale `unavailable` (`custom_components/modbus_solar/adapters/inbound/coordinator.py:56-60`).

No hay reintento agresivo: se reintenta en el siguiente tick del tier (spec §5, `docs/changes/2026-10-04-skeleton/spec.md:353-355`). Cuando la lectura vuelve a funcionar, el equipo se recupera solo. Los dos perfiles Ingeteam espacian las peticiones 1 s, como recomienda Ingeteam (`custom_components/modbus_solar/profiles/ingeteam/oneplay.py:11-12`, `custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:95-96`).

## Cambio de perfil en equipos ya configurados

Hasta la versión `0.1.0b1`, el id `ingeteam.oneplay_storage` leía el mapa del 1Play sin storage (`ACL2010IMB05`). Ahora lee el del STORAGE 1Play TL M (`ABH2010IMB08`). Un equipo ya configurado con ese id pasa al mapa nuevo sin migrar la subentry.

- `inverter_state` y `active_power` conservan clave y `unique_id`. Cambian su registro y las opciones del enum.
- `total_energy` ya no existe en el perfil. Su entidad queda huérfana en el entity registry: HA la marca como que la integración ya no la proporciona. Se borra a mano desde la UI. Sus estadísticas no pasan a `solar_energy`.
