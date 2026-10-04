---
status: accepted
date: 2026-10-04
---

# 0001 — Hexagonal estricto con import-linter

## Contexto

Las integraciones de Home Assistant suelen mezclar protocolo, lógica y entidades en los mismos módulos. Se quieren tests sin HA para la lógica.

## Decisión

Capas `domain`, `ports`, `application` y `adapters`, más `profiles` (datos de cada equipo). Los contratos viven en `pyproject.toml` (`[tool.importlinter]`, `pyproject.toml:21-61`) y los verifica `lint-imports` en el job `lint` del CI (`.github/workflows/tests.yml:22-24`) y en `scripts/lint.sh:12`.

## Consecuencias

- `domain`, `ports`, `application` y `profiles` no importan `homeassistant` ni `modbus_connection` (`pyproject.toml:35-44`).
- La raíz del paquete (`__init__.py`, `config_flow.py`) compone: es el único sitio donde se unen catálogo, gateway y adaptadores de HA (`custom_components/modbus_solar/__init__.py:11-17`, `custom_components/modbus_solar/config_flow.py:11-17`).
- Un import prohibido rompe el job `lint`.
- Los contratos no se relajan para que pase un import: se mueve el código.
