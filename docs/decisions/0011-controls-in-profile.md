---
status: accepted
date: 2026-10-04
---

# 0011 — Los controles escribibles se declaran en el perfil

## Contexto

Hasta ahora la integración solo leía. El perfil es declarativo ([ADR 0002](0002-python-profiles.md)) y el STORAGE 1Play TL M necesita escribir el comando 26 «Battery Control Values», dato 1 «Grid power» (`AAA0030IMB03_N` págs. 7 y 19-20).

Alternativas descartadas:

- Una clase de entidad por parámetro, con los registros dentro del adaptador: la marca dejaría de ser dato del perfil y cada parámetro nuevo sería código de HA.
- Ampliar `DeviceGateway` con `write`: el poller y el config flow solo leen y no deben poder escribir.

## Decisión

El perfil declara los controles como datos. La escritura es dominio puro hasta el puerto.

- `WriteSpec` (dirección, palabras fijas, tipo, escala) y `GatedLimitSpec` (un límite con su interruptor) están en `custom_components/modbus_solar/domain/control.py:8-30`. `GatedState.effective` da lo que el equipo debe tener: el límite si el switch está activo, `off_value` si no (`custom_components/modbus_solar/domain/control.py:33-42`).
- `DeviceProfile.controls` los lista (`custom_components/modbus_solar/domain/profile.py:50`). `Role` gana `EXPORT_LIMIT` y `EXPORT_ENABLED` (`custom_components/modbus_solar/domain/types.py:59-60`).
- `encode` convierte el valor en palabras y está en el dominio (`custom_components/modbus_solar/domain/encode.py:9-19`).
- `DeviceWriter` es un puerto aparte de `DeviceGateway` (`custom_components/modbus_solar/ports/device.py:16-21`). `ModbusGateway` implementa los dos (`custom_components/modbus_solar/adapters/outbound/modbus_gateway.py:33-60`).
- Los casos de uso `set_limit` y `set_enabled` validan, escriben y solo entonces cambian el estado (`custom_components/modbus_solar/application/control.py:9-20`).
- `number` y `switch` son plataformas genéricas: crean una entidad por cada control del perfil (`custom_components/modbus_solar/adapters/inbound/entities/factory.py:56-63`).
- El STORAGE declara su control en `custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:250-265`.

## Consecuencias

- Otro parámetro con interruptor es un `GatedLimitSpec` más en el perfil. Puerto, gateway, `WriteSpec` y `encode` no cambian.
- Un parámetro de otra forma (por ejemplo, una lista de opciones) necesita un dataclass de control nuevo y su plataforma. El resto de la pila se reutiliza.
- Solo hay escrituras de 16 bits: `validate_profile` rechaza otro tipo (`custom_components/modbus_solar/domain/validate.py:31-32`).
- El valor se valida dos veces: en el caso de uso (rango del control) y en `encode` (rango del tipo).
- Los perfiles sin `controls` no crean ninguna entidad `number` ni `switch`.
