---
status: accepted
date: 2026-10-04
---

# 0006 — Solo PDF oficiales

## Contexto

La documentación Modbus de los fabricantes circula en copias no oficiales, a veces de revisiones distintas.

## Decisión

En `docs/wiki/brands/` solo entran PDF oficiales y públicos, con SHA-256 y revisión. La procedencia de cada PDF está en `docs/wiki/brands/ingeteam/README.md`.

## Consecuencias

- Un registro sin fuente oficial no entra en un perfil. El perfil actual cita la página del PDF en cada decisión (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:1`, `:11`, `:25`).
- Una revisión anterior de un PDF se descarta: la F de `AAA0030IMB03` es anterior a la N y no entra (`docs/changes/2026-10-04-skeleton/spec.md:536-537`).
