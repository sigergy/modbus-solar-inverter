---
status: accepted
date: 2026-10-06
---

# 0017 — Modo de medición de red elegido a mano

Amplía [0009](0009-computed-energy.md), [0015](0015-device-per-component.md) y [0016](0016-instant-tier.md).

## Contexto

En el STORAGE 1Play TL M el intercambio con la red lo mide un vatímetro u otro según la instalación (`docs/wiki/brands/ingeteam/storage-1-play-tl-m/ABH2014IQM01.pdf`, apdo. 19.8, pág. 60):

- con vatímetro externo en el punto de conexión, el externo (registro 30072);
- sin vatímetro externo, con todas las cargas en la salida de cargas críticas, el interno (registro 30052);
- en aislada, el interno, y las bornas de red pueden llevar un grupo electrógeno: la entrada «grid/genset» (apdo. 11, pág. 32).

Hasta ahora las energías de red integraban siempre 30072. En una instalación sin vatímetro externo eran falsas.

Ningún registro dice qué vatímetro usa el equipo. CMD 18 «Self-Consumption Activation», opción 2 «Self-Consumption mode to CG Wattmeter», es un comando de escritura (`AAA0030IMB03_N`, pág. 6); en esa misma página la fila de CMD 18 está marcada «n/a» para el 1PLAY SUN STORAGE TL M. El mapa de lectura no lo trae (`ABH2010IMB08`).

## Decisión

- El perfil declara modos de medición, `metering_modes` (`custom_components/modbus_solar/domain/profile.py:67-68`). Cada modo es un `MeteringModeSpec` con la potencia leída que hace de fuente, el componente de sus entidades y sus flujos (`custom_components/modbus_solar/domain/metering.py:9-25`).
- Un solo desplegable, «Medición de red». El modo decide a la vez la fuente, las entidades y el dispositivo (`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:448-467`):

| Modo | Fuente | Entidades | Dispositivo |
|---|---|---|---|
| Consumos en Grid (por defecto) | 30072 | Potencia de red, Potencia a la red, Energía importada, Energía exportada | Red |
| Consumos en Cargas Críticas | 30052 | las mismas cuatro | Vatímetro interno |
| Aislada | 30052 | Potencia del generador, Energía del generador | Generador |

- La elección es manual, en el alta y en reconfigurar, sin sugerencia automática: no hay registro que identifique el vatímetro (`custom_components/modbus_solar/adapters/inbound/flow.py:460-483`, `:762-772`).
- Las potencias son derivadas: la fuente filtrada por signo con `filter_power` (`custom_components/modbus_solar/domain/energy.py:16-20`). Cada energía integra la misma fuente con el mismo signo (`custom_components/modbus_solar/application/selection.py:48-72`).
- El vatímetro del modo es un componente forzado: sale marcado en «Componentes» y desmarcarlo da error (`custom_components/modbus_solar/adapters/inbound/flow.py:242-245`, `:512-517`).
- El modo se guarda en la entry como `metering`. Una entry sin la clave toma el primer modo, «Consumos en Grid». Sin migración (`custom_components/modbus_solar/application/selection.py:21-25`).

## Consecuencias

- Las energías de red conservan clave, `unique_id` e historial entre «Consumos en Grid» y «Consumos en Cargas Críticas»: cambian de fuente y de dispositivo.
- Pasar a «Aislada» borra las entidades de red con su historial; salir de «Aislada» borra las del generador y el dispositivo Generador (`custom_components/modbus_solar/__init__.py:28-64`).
- Una entry existente toma «Consumos en Grid», que fuerza la Red (`custom_components/modbus_solar/application/selection.py:42-44`). Con Red elegida se comporta como antes, más las dos potencias de red nuevas. Sin Red elegida, recupera el dispositivo Red con sus entidades; para quitarlo hay que reconfigurar y elegir «Consumos en Cargas Críticas».
- Con «Consumos en Cargas Críticas» o «Aislada» las energías de red siguen al tier `fast` de 30052, no al `instant` de 30072 que fija [0016](0016-instant-tier.md).
- Un modo mal elegido da cifras falsas sin aviso: la integración no puede comprobarlo.
- Los signos de 30072 y 30052 son supuestos, > 0 = entra potencia por las bornas de red. Se verifican en la VM.
- Un perfil sin modos no cambia: no hay paso de medición.
