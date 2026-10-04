---
status: accepted
date: 2026-10-04
---

# 0009 — Energía calculada por la integración cuando el equipo no la da

## Contexto

El mapa del INGECON SUN STORAGE 1Play TL M (`ABH2010IMB08`) no trae ningún contador de energía. Sí da la potencia de los MPPT, de la red y de la batería. El panel de Energía de HA necesita sensores `energy` con `state_class=total_increasing`.

Alternativas descartadas:

- Que el usuario cree helpers «Integral» de HA a mano: cinco helpers por equipo, sin filtro de signo, y dependen de que los sensores de potencia estén habilitados.
- Buscar contadores en la API HTTP del inversor (`AAA0060IMB05`): sería un segundo transporte además de Modbus. No se ha comprobado si la API los da.

## Decisión

La integración integra la potencia y expone los contadores como entidades propias.

- El perfil declara las energías como datos: `EnergySpec(key, role, sources, sign)` en `DeviceProfile.energies` (`custom_components/modbus_solar/domain/energy.py:16-22`, `custom_components/modbus_solar/domain/profile.py:49`).
- El cálculo es dominio puro: `EnergyAccumulator` aplica la regla del trapecio sobre la suma de las fuentes filtrada por signo (`custom_components/modbus_solar/domain/energy.py:25-50`).
- `validate_profile` exige fuentes existentes, de potencia y del mismo tier (`custom_components/modbus_solar/domain/validate.py:60-72`).
- La entidad `ModbusSolarEnergySensor` es un `RestoreSensor` en kWh (`custom_components/modbus_solar/adapters/inbound/entities/energy.py:14-18`).
- El tier con fuentes de energía usa `always_update=True` (`custom_components/modbus_solar/adapters/inbound/runtime.py:70-71`, `:81`): con potencia constante el `TierResult` no cambia, y sin aviso no habría muestras.

## Consecuencias

- La energía es una aproximación: su precisión depende del intervalo del tier `fast`.
- No se integra un tramo con lectura fallida, ni uno de más de 3 intervalos del tier, ni el tiempo con HA apagado. La energía de esos tramos se pierde: nunca se inventa.
- Tras reiniciar, el total sigue desde el último valor guardado por HA.
- Las fuentes de una energía activa se leen aunque su sensor de potencia esté deshabilitado (`custom_components/modbus_solar/adapters/inbound/runtime.py:53-56`).
- Un tier con energías escribe estado en cada lectura, aunque los valores no cambien.
- Un perfil cuyo equipo sí da contadores no declara `energies` y no cambia nada.
