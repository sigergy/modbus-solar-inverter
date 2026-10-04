---
status: proposed
date: 2026-10-04
---

# 0015 — Un dispositivo por componente dentro de la entry

Matiza [0010](0010-entry-per-device.md): sigue una entry por equipo físico, pero la entry deja de tener un único
dispositivo.

## Contexto

Con 0010 cada entry crea un único dispositivo, `(DOMAIN, entry_id)`
(`custom_components/modbus_solar/adapters/inbound/entities/base.py:36-41`). El STORAGE 1Play TL M expone por una
sola IP datos del inversor, campo solar, batería, red, vatímetro interno, cargas críticas, consumo y cargador VE:
47 entidades en un dispositivo. Una instalación sin cargador VE o sin cargas críticas no puede quitarlas. Los bits
del BMS añadirían 14 más.

## Decisión

- Una entry sigue siendo un equipo físico, con `unique_id` = `host:puerto:unidad` (0010).
- Dentro de la entry, un dispositivo de HA por componente elegido en el alta
  (`docs/changes/2026-10-04-setup-flow-v2/spec.md`, §5):
  - el principal conserva `(DOMAIN, entry_id)`;
  - cada opcional usa `(DOMAIN, f"{entry_id}_{component}")` y `via_device` hacia el principal.
- El título de la entry agrupa los dispositivos, que llevan nombre corto traducido («Inversor», «Batería»).
- `integration_type` pasa de `device` a `hub` (`custom_components/modbus_solar/manifest.json:8`).

## Consecuencias

- El `unique_id` de las entidades no cambia (`custom_components/modbus_solar/adapters/inbound/entities/base.py:30`):
  pasar una entidad a otro dispositivo conserva su historial.
- Desmarcar un componente borra sus entidades y su dispositivo del registro, con su historial.
- Con dos entries del mismo modelo, las entidades nuevas de la segunda reciben `entity_id` con sufijo `_2`.
- Una entry creada antes, sin componentes guardados, toma todos los del perfil.
