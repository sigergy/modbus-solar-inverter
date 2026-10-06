# Funcionalidad: control del vertido a red

Documento vivo. Rutas bajo `custom_components/modbus_solar/` salvo indicación. Solo el perfil `ingeteam.oneplay_storage` declara controles (`profiles/ingeteam/oneplay_storage.py:89-102`, `:468`); `ingeteam.oneplay` no crea ninguna entidad `number` ni `switch`. Nombres de las entidades en `strings.json:495-504`.

## Entidades

| Entidad | Plataforma | Clave | Rango | Qué hace |
|---|---|---|---|---|
| Límite de vertido a red | `number` | `export_limit` | 0-6000 W, paso 1, modo caja | Potencia máxima que el equipo inyecta a la red |
| Vertido a red | `switch` | `export_enabled` | — | ON: vertido activado. OFF: vertido desactivado |

Rango, paso, unidad y valor por defecto salen de la declaración del perfil (`profiles/ingeteam/oneplay_storage.py:96-101`). El máximo de 6000 W es el del rango del PDF (`AAA0030IMB03_N` pág. 7), no el de la ficha del equipo.

Son dos entidades independientes: apagar el switch no cambia el valor del number (`tests/ha/test_control.py:157-169`). Un solo `GatedLimitSpec` da las dos (`domain/control.py:16-30`, ADR [0011](../decisions/0011-controls-in-profile.md)).

## Qué se escribe

Una escritura FC16 de tres palabras en la dirección 1000, en una sola trama: `[26, 0x0A, W]`. Código 26 (`0x1A`) «Battery Control Values», dato 1 `0x0A` «Grid power», dato 2 los vatios (`AAA0030IMB03_N` págs. 7 y 19-20; `profiles/ingeteam/oneplay_storage.py:78-81`, `:94-95`). Con FC16 código y datos van en la misma escritura (`AAA0030IMB03_N` pág. 8, Nota 3; `adapters/outbound/modbus_gateway.py:56-60`).

| Acción | Palabras |
|---|---|
| Switch → ON | `[26, 10, valor del number]` |
| Switch → OFF | `[26, 10, 0]` |
| Number cambia con el switch ON | `[26, 10, valor nuevo]` |
| Number cambia con el switch OFF | no escribe; guarda el valor para el próximo ON |

La regla es `GatedState.effective`: el límite con el switch activo, `off_value` (0 W) con el switch apagado (`domain/control.py:40-42`). Los casos de uso son `set_limit` y `set_enabled` (`application/control.py:9-20`). 0 W equivale a «no inyectar excedente a la red» (`ABH2014IQM01` apdo. 19.7.7, pág. 54).

El valor se codifica con `encode`: `round(valor / scale)`, dentro del rango de 16 bits (`domain/encode.py:9-19`). Los extremos del rango y `off_value` se comprueban al validar el perfil (`domain/validate.py:39-45`).

## Estado optimista y restaurado

El equipo no tiene registro de lectura de este ajuste (ADR [0012](../decisions/0012-optimistic-restored-state.md)). HA muestra lo último que escribió y lo restaura tras reiniciar, sin escribir al equipo.

- Primer arranque: number a 6000 W y switch ON, sin escribir nada (`adapters/inbound/runtime.py:109-110`; `tests/ha/test_control.py:74-81`, `:142-149`).
- Restaurar no escribe: el inversor conserva lo que tenía (`adapters/inbound/entities/number.py:24-30`, `adapters/inbound/entities/switch.py:23-28`; `tests/ha/test_control.py:115-121`, `:200-213`). Un valor restaurado fuera del rango se ignora (`adapters/inbound/entities/number.py:29`).
- Sobrevive a recargar la entry y no vuelve a escribir (`tests/ha/test_control.py:216-228`).
- El switch lleva `assumed_state` (`adapters/inbound/entities/switch.py:17-18`).
- Si alguien cambia el vertido desde los ajustes del inversor, HA no se entera.
- El sensor extra `power_reduction_reason` (registro 30042, valor 16 «PV Surplus Injected to the Grid») indica que el inversor está limitando por este motivo ahora mismo (`profiles/ingeteam/oneplay_storage.py:312`; `ABH2010IMB08` Nota 7, pág. 7). No da el valor del ajuste.

## Disponibilidad y errores

- Number y switch cuelgan del coordinator del tier de `probe_key`, `inverter_state` en el STORAGE (`adapters/inbound/entities/factory.py:65-68`, `profiles/ingeteam/oneplay_storage.py:203`, `:215-223`). Nacen `unavailable` hasta la primera lectura correcta y vuelven a `unavailable` si el equipo cae: con el equipo sin responder no se ofrece escribir (`tests/ha/test_control.py:124-139`, `:231-236`).
- Una escritura fallida lanza `HomeAssistantError` con el mensaje traducible `write_failed` y no cambia el estado (`adapters/inbound/entities/control.py:16-24`, `strings.json:506-510`; `tests/ha/test_control.py:99-112`, `:184-197`). Cubre `DeviceUnavailable`, `DeviceProtocolError` y `EncodeError`.
- Una escritura espera detrás de las lecturas en curso: `modbus_connection` espacia las peticiones de la unit y no mezcla tramas. Un ciclo de lectura largo retrasa la escritura unos segundos (`docs/changes/2026-10-04-export-control/spec.md` §2.2).

## Pendiente de verificar en el equipo

- Si el CMD 26 sobrevive a un reinicio del inversor: el PDF no lo dice.
- Si el comando aplica solo con la batería configurada como «Lead-Acid» o «Ingeteam RS485 Protocol» (`AAA0030IMB03_N` pág. 19).

## Fuera de alcance

- Potencia contratada y máxima potencia de consumo de red: ningún documento da registro ni comando (`docs/wiki/brands/ingeteam/README.md`).
- Otros parámetros de batería: se añaden como controles nuevos en el perfil.
- Leer el valor real del ajuste: ver ADR [0012](../decisions/0012-optimistic-restored-state.md).

Diseño: `docs/changes/2026-10-04-export-control/spec.md`. Arquitectura: [domain](../architecture/domain.md), [ports](../architecture/ports.md), [application](../architecture/application.md), [inbound](../architecture/adapters/inbound.md), [outbound](../architecture/adapters/outbound.md).
