---
status: superseded by 0010
date: 2026-10-04
---

# 0004 — Entry = marca, subentry = equipo

## Contexto

Se quieren varios equipos de una misma marca bajo un único punto de configuración.

## Decisión

Una config entry por marca, con `unique_id` = marca (`custom_components/modbus_solar/adapters/inbound/flow.py:58-61`). Cada equipo es una subentry de tipo `device` (`custom_components/modbus_solar/const.py:10`) con `unique_id` = `host:puerto:unidad` (`custom_components/modbus_solar/adapters/inbound/flow.py:45-46`).

## Consecuencias

- Alta, baja o reconfigure de un equipo recarga la entry de marca entera (`custom_components/modbus_solar/__init__.py:51-52`, `:60-61`). Es necesario: `async_get_unit` ata la liberación de la conexión a la entry, no a la subentry (`docs/changes/2026-10-04-skeleton/spec.md:304-307`).
- Aceptable: las altas y bajas de equipos son operaciones raras.
- El `unique_id` de las entidades usa el `subentry_id`, no el host: cambiar el host no duplica entidades (`custom_components/modbus_solar/adapters/inbound/runtime.py:30-32`).
