---
status: accepted
date: 2026-10-04
---

# 0002 — Perfiles en Python

## Contexto

Cada equipo necesita registros, escalas, tiers de sondeo y metadatos de entidad.

## Decisión

Los perfiles son instancias de `DeviceProfile` (`custom_components/modbus_solar/domain/profile.py:36-46`) en `custom_components/modbus_solar/profiles/<marca>/`. Hoy hay uno: `ONEPLAY_STORAGE` (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:7`). `validate_profile` (`custom_components/modbus_solar/domain/validate.py:48`) los comprueba en tests.

## Consecuencias

- Sin parser ni esquema JSON en esta fase.
- SunSpec por escaneo: spec 3.
- Exportar e importar perfiles en JSON: última fase.
- Un perfil nuevo es un fichero Python que solo importa `domain` (`pyproject.toml:46-50`) y se añade a `ALL_PROFILES` (`custom_components/modbus_solar/profiles/__init__.py:6`).
