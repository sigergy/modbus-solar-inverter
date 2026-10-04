---
status: accepted
date: 2026-10-04
---

# 0007 — Tests solo en CI

## Contexto

La máquina de desarrollo es Windows y Home Assistant no se instala allí.

## Decisión

`pytest` solo corre en GitHub Actions (job `test`, `.github/workflows/tests.yml:28-43`). En local solo se ejecuta `scripts/lint.sh`: ruff, `lint-imports` y compileall, sin tests (`scripts/lint.sh:2`, `:9-13`).

## Consecuencias

- TDD con commits `test(red): …` que se empujan y se esperan con `scripts/ci-wait.sh` (`scripts/ci-wait.sh:2-6`).
- Cada ciclo RED/GREEN cuesta minutos de CI.
- Las pruebas visuales y de integración van a la VM de desarrollo, no a esta máquina.
