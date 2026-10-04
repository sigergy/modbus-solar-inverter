---
status: accepted
date: 2026-10-04
---

# 0003 — Conexión compartida del core

## Contexto

El Ingeteam admite un solo cliente Modbus (`docs/changes/2026-10-04-skeleton/spec.md:66`). HA 2026.9 expone `async_get_unit` y `async_get_temporary_unit` en la integración `modbus` (`docs/changes/2026-10-04-skeleton/spec.md:51-52`).

## Decisión

La conexión se obtiene de `homeassistant.components.modbus` y se usa a través de `modbus-connection`. Sin pymodbus directo. El manifest declara `"dependencies": ["modbus"]` y `"requirements": []` (`custom_components/modbus_solar/manifest.json:6`, `:11`).

- Setup: `async_get_unit` (`custom_components/modbus_solar/__init__.py:27-28`).
- Config flow: `async_get_temporary_unit` (`custom_components/modbus_solar/config_flow.py:27-29`).

## Consecuencias

- Varias entries comparten una conexión por endpoint.
- El espaciado entre peticiones lo aplica la librería: `ModbusGateway` llama a `set_message_spacing` con `profile.min_request_interval_s` (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:39`).
- Si el endpoint ya está abierto con otros parámetros de enlace, la apertura lanza `HomeAssistantError`. El config flow lo traduce a `EndpointInUse` (`custom_components/modbus_solar/config_flow.py:30-32`).
- Los tests usan `modbus_connection.mock` (`tests/ha/conftest.py:9`, `tests/unit/test_modbus_gateway.py:6`).
- Los pines de `pymodbus`, `modbus-connection` y `tmodbus` son los del manifest de `modbus` de HA 2026.9 (`.github/workflows/tests.yml:36-41`).
