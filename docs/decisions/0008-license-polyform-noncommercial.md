---
status: accepted
date: 2026-10-04
---

# 0008 — PolyForm Noncommercial 1.0.0

## Contexto

Proyecto sin uso comercial previsto.

## Decisión

`LICENSE` es PolyForm Noncommercial 1.0.0 con `Required Notice` (`LICENSE:1-3`).

## Consecuencias

- Se puede relajar a AGPL-3.0 más adelante. No se puede endurecer: las versiones ya publicadas conservan su licencia.
- PolyForm Noncommercial no es una licencia aprobada por OSI, así que `hacs/action` ignora el check `license` (`.github/workflows/validate.yml:21-22`).
