---
status: accepted
date: 2026-10-04
---

# 0010 — Una config entry por equipo

Sustituye a [0004](0004-entry-brand-subentry-device.md).

## Contexto

Con 0004 el alta tenía dos niveles: primero la entry de marca, después «Añadir equipo» como subentry. En la instalación real el flujo no se entendía: el usuario no encontraba dónde poner la IP ni elegir el modelo. Además, «Añadir equipo» se quedaba cargando sin fin y no había forma de saber si el equipo respondía (`docs/changes/2026-10-04-setup-flow/spec.md`).

## Decisión

- Una config entry por inversor, con `unique_id` = `host:puerto:unidad` (`custom_components/modbus_solar/adapters/inbound/flow.py:51-52`, `:104-105`).
- Flow de tres pasos: modelo, conexión y confirmación con lecturas reales (`custom_components/modbus_solar/adapters/inbound/flow.py:84-155`).
- La sonda tiene un tiempo máximo de 20 s (`custom_components/modbus_solar/adapters/inbound/flow.py:48`, `:202-205`).
- `integration_type` pasa a `device` (`custom_components/modbus_solar/manifest.json:8`).
- `VERSION = 2` (`custom_components/modbus_solar/adapters/inbound/flow.py:76`). Las entries v1 no se migran: el setup falla con `MIGRATION_ERROR` y un mensaje en el log (`custom_components/modbus_solar/__init__.py:47-55`).

## Consecuencias

- Alta, baja o reconfigure de un equipo solo recarga su entry. `async_get_unit` ata la conexión a la entry y la comparte por endpoint (ADR [0003](0003-modbus-shared-connection.md)).
- Sin dispositivo de marca ni `via_device_id`: cada entry tiene un único dispositivo, `(DOMAIN, entry_id)` (`custom_components/modbus_solar/adapters/inbound/entities/base.py:36-37`).
- El `unique_id` de las entidades usa el `entry_id`, no el host: cambiar el host no duplica entidades (`custom_components/modbus_solar/adapters/inbound/runtime.py:33-35`).
- Quien tenga una entry v1 la borra y añade cada inversor de nuevo. Los históricos de las entidades viejas no pasan a las nuevas.
