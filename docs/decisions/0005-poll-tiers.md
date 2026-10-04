---
status: accepted
date: 2026-10-04
---

# 0005 — Tiers de sondeo

## Contexto

Hay valores que cambian cada segundo y otros que cambian cada hora.

## Decisión

Tres tiers, `fast`, `normal` y `slow` (`custom_components/modbus_solar/domain/types.py:27-30`), de 5, 60 y 3600 s (`custom_components/modbus_solar/const.py:13`). Un `TierCoordinator` por tier con entidades (`custom_components/modbus_solar/adapters/inbound/runtime.py:57-70`). Los intervalos se editan en el reconfigure del equipo, con el mínimo `min_tier_interval` del perfil (`custom_components/modbus_solar/application/poller.py:46-49`, `custom_components/modbus_solar/adapters/inbound/flow.py:125-128`).

## Consecuencias

- Las entidades deshabilitadas no se leen: `read_tier` solo pide las claves habilitadas (`custom_components/modbus_solar/application/poller.py:27-28`).
- Un intervalo menor que el tiempo de lectura del tier se rechaza en el formulario con `interval_too_short` (`custom_components/modbus_solar/adapters/inbound/flow.py:127-128`).
- Un tier es todo o nada: si falla un bloque, falla el tier entero (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:34-39`).
