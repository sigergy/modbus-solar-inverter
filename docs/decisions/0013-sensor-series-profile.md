---
status: accepted
date: 2026-10-04
---

# 0013 — Un perfil por serie de sensores, con registros opcionales activos

## Contexto

La serie Si-RS485TC-…-MB de Ingenieurbüro Mencke & Tegtmeyer tiene cuatro modelos con la misma tabla
de registros. Cada modelo activa un subconjunto (`Specification_Si-RS485_MODBUS.pdf` pág. 5). Un
registro opcional que el sensor no soporta devuelve 0, no un error (pág. 1). El modelo y el firmware
solo se leen con la función 0x46 (págs. 4-5), y `DeviceGateway` solo lee registros
(`custom_components/modbus_solar/ports/device.py:10-13`).

Alternativas descartadas:

- Un perfil por modelo: cuatro literales casi iguales, y el usuario tendría que saber qué modelo tiene.
- Leer el modelo por FC 0x46 y filtrar entidades: requiere ampliar el puerto del equipo. Fuera del
  alcance de esta spec.

## Decisión

Un solo perfil `mencke_tegtmeyer.si_rs485` para toda la serie
(`custom_components/modbus_solar/profiles/mencke_tegtmeyer/si_rs485.py:7`). Declara los cuatro registros
y las cuatro entidades están activas por defecto, aunque un modelo no las tenga. Un solo bloque FC04
de 9 registros con `max_gap=3` (`si_rs485.py:16`).

## Consecuencias

- Los modelos sin viento o sin temperatura externa muestran 0 m/s o 0 °C como si fueran medidas, porque
  un registro ausente devuelve 0. El usuario deshabilita esa entidad desde la UI de HA.
- Los registros 7 y 8 no responden con datos reales en firmware < 1.53 (pág. 1). Fuera de alcance.
- Si el falso 0 molesta, la salida es leer el modelo por FC 0x46 y filtrar entidades, o un perfil por
  modelo. Ninguna está decidida.
