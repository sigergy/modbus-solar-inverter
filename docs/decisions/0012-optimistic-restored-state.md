---
status: accepted
date: 2026-10-04
---

# 0012 — Estado optimista y restaurado para los ajustes que no se pueden leer

## Contexto

Ningún documento da un registro que lea el ajuste «Grid power» (`AAA0030IMB03_N` pág. 4; `ABH2010IMB08`). El comando 26 solo se escribe.

Alternativas descartadas:

- Leer el registro 30042 «Active Power Reduction Reason»: solo dice si el inversor limita ahora por este motivo, no cuál es el ajuste (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:271`).
- Leer los holding 1000-1002: son la zona de comandos y no documentan el último valor aplicado.
- Escribir al arrancar HA para sincronizar: cambiaría el equipo sin que el usuario lo pida.

## Decisión

HA muestra lo último que escribió y lo recupera tras reiniciar. No escribe al equipo para sincronizarlo.

- El estado vive en memoria, uno por control, compartido por su number y su switch (`custom_components/modbus_solar/adapters/inbound/runtime.py:94-95`; `GatedState` en `custom_components/modbus_solar/domain/control.py:33-38`).
- Sin valor restaurado manda `default` y el switch arranca en ON.
- El number es `RestoreNumber` y el switch `RestoreEntity`. Restaurar solo carga el estado y nunca escribe (`custom_components/modbus_solar/adapters/inbound/entities/number.py:24-30`, `custom_components/modbus_solar/adapters/inbound/entities/switch.py:23-28`). Un número restaurado fuera del rango se ignora.
- El switch declara `assumed_state` (`custom_components/modbus_solar/adapters/inbound/entities/switch.py:17-18`).
- `ModbusGateway.write` no relee tras escribir: no hay nada que contrastar (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:56-60`).
- Una escritura fallida no cambia el estado (`custom_components/modbus_solar/application/control.py:12-15`, `:19-20`).

## Consecuencias

- Los cambios hechos desde los ajustes del inversor no se reflejan en HA.
- Si el inversor se reinicia y pierde el ajuste, HA sigue mostrando el anterior. El PDF no dice si el comando 26 sobrevive a un reinicio.
- Si aparece un registro de lectura, se añade sin cambiar el modelo: el estado pasa a venir del equipo y la restauración deja de ser necesaria para ese control.
- Primer arranque: límite a 6000 W y switch ON, sin escribir nada.
- Tras una escritura, el estado de HA puede diferir del real si el inversor la ignora sin error. Se comprueba en el equipo ([features/control](../features/control.md)).
