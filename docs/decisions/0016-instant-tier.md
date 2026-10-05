---
status: accepted
date: 2026-10-05
---

# 0016 — Tier `instant` y presupuesto de una petición por segundo

Amplía [0005](0005-poll-tiers.md): los tiers pasan de tres a cuatro.

## Contexto

La red (tensión, frecuencia y potencia) cambia más deprisa que el resto de medidas y interesa verla antes. Ingeteam pide al menos 1 s entre peticiones y como mucho 10 registros por petición, con un único cliente (`docs/wiki/brands/ingeteam/storage-1-play-tl-m/ABH2014IQM01.pdf`, apdo. 19.6.1, pág. 50). El espaciado es de la conexión (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:39`) y lo comparten todos los tiers: un tier más rápido no acelera el equipo, reparte el mismo segundo.

## Decisión

- Tier nuevo `PollTier.INSTANT = "instant"`, el primero del enum (`custom_components/modbus_solar/domain/types.py:31`). Intervalo por defecto 5 s; `fast` pasa a 10 s (`custom_components/modbus_solar/const.py:13`).
- Va en `instant` solo la red del STORAGE: `grid_voltage`, `grid_frequency` y `grid_power` (30070-30072, un bloque de 3 registros) y las energías de red que siguen a `grid_power`. Ninguna entidad de diagnóstico va en `instant`.
- Presupuesto de una petición por segundo: `request_rate` suma `min_tier_interval(tier) / intervalo(tier)` de los tiers del formulario (`custom_components/modbus_solar/application/poller.py:52-54`). El alta y reconfigure lo rechazan por encima de `MAX_REQUEST_RATE` con `interval_budget_exceeded` (`custom_components/modbus_solar/adapters/inbound/flow.py:147`, `:220-232`). Se comprueba después de `interval_too_short`.
- La sonda lee `fast` e `instant` (`custom_components/modbus_solar/application/probe.py:25-26`): el paso de lecturas sigue mostrando la red.
- Una entry anterior sin la clave `instant` toma el valor por defecto: `build_runtime` mezcla `DEFAULT_INTERVALS` con los de la entry (`custom_components/modbus_solar/adapters/inbound/runtime.py:77`). Sin migración.

STORAGE con todos los componentes y los intervalos por defecto:

| Tier | Bloques | Intervalo | Peticiones/s |
|---|---|---|---|
| `instant` | 1 | 5 s | 0,20 |
| `fast` | 6 | 10 s | 0,60 |
| `normal` | 5 | 60 s | 0,08 |
| `slow` | 3 | 3600 s | 0,00 |
| Total | | | 0,88 |

## Consecuencias

- `ingeteam.oneplay` y el sensor de irradiancia no tienen registros de red: no tienen tier `instant` y el formulario no le da sección (`custom_components/modbus_solar/adapters/inbound/flow.py:150-152`).
- Con `fast` 10 s y `normal` 60 s, `instant` admite 4 s (0,93 peticiones/s); 3 s ya no (1,02).
- Un STORAGE de una versión anterior conserva `fast` 5 s: puede pedir algo más de una petición por segundo. El espaciado encola las lecturas y los ciclos se retrasan un poco; no hay error. Al reconfigurar, el presupuesto lo corrige.
- `instant` a 5 s da más estados al día en el recorder para las tres entidades de red.
