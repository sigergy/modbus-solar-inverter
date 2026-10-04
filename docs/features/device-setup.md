# Funcionalidad: alta y configuración de equipos

Documento vivo. Rutas bajo `custom_components/modbus_solar/` salvo indicación. Los nombres de campo y de error son las claves de `strings.json`.

## Alta de un inversor

Una config entry por inversor (ADR [0010](../decisions/0010-entry-per-device.md)). «Añadir integración» → Modbus Solar abre un flow de tres pasos (`adapters/inbound/flow.py:73-155`).

### Paso 1 · modelo (`user`)

- Campo `profile`, una lista con un perfil por línea (`adapters/inbound/flow.py:84-94`).
- Etiqueta `"{marca} · {modelos}"`: `Ingeteam · 1Play TL M` y `Ingeteam · STORAGE 1Play TL M`. Orden: marca y después `id` (`application/catalog.py:16-20`).
- Para un STORAGE 1Play TL M hay que elegir `Ingeteam · STORAGE 1Play TL M` (`ingeteam.oneplay_storage`).

### Paso 2 · conexión (`connection`)

| Campo | Valor por defecto | Rango |
|---|---|---|
| `host` | — | texto |
| `port`, en la sección plegada `advanced` | `profile.default_port` (502 en Ingeteam) | 1-65535 |
| `unit_id`, en la sección plegada `advanced` | `profile.default_unit_id` (1 en Ingeteam) | 1-247 |

Esquema en `adapters/inbound/flow.py:119-132`; rangos en `:42-43`. Puerto y unidad por defecto de los dos perfiles Ingeteam: `profiles/ingeteam/oneplay.py:14-15` y `profiles/ingeteam/oneplay_storage.py:107-108`.

Abort `already_configured`: mismo `host:port:unit_id`, con el host en minúsculas (`adapters/inbound/flow.py:51-52`, `:104-105`). Se comprueba antes de abrir conexión.

#### Sonda

Al enviar, el flow abre una unit temporal (`config_flow.py:20-33`) y llama a `probe_device` (`application/probe.py:10-17`):

1. Lee la entidad `probe_key` del perfil, `inverter_state` en los dos perfiles Ingeteam: input 30016 en el STORAGE (`profiles/ingeteam/oneplay_storage.py:109`, `:114`) y holding `0x101D` en el 1Play sin storage (`profiles/ingeteam/oneplay.py:16`, `:22`). Un valor fuera del enum lanza `DecodeError`.
2. Lee el tier `fast`, limitado a las entidades habilitadas por defecto.

Todo dentro de un tiempo máximo de `PROBE_TIMEOUT_S = 20` s (`adapters/inbound/flow.py:48`, `:202-205`). Si falla, no se crea la entry y el formulario vuelve con lo que escribió el usuario (`adapters/inbound/flow.py:133-137`).

#### Errores del formulario

| Error | Cuándo | Origen |
|---|---|---|
| `cannot_connect` | el equipo no responde o la sonda supera 20 s | `DeviceUnavailable` o `TimeoutError` (`adapters/inbound/flow.py:110-111`) |
| `endpoint_in_use` | el endpoint ya está en uso con otros parámetros de enlace | `HomeAssistantError` de `async_get_temporary_unit`, traducido a `EndpointInUse` (`config_flow.py:30-32`, `adapters/inbound/flow.py:108-109`) |
| `invalid_response` | excepción Modbus o valor fuera del enum | `DeviceProtocolError` o `DecodeError` (`adapters/inbound/flow.py:112-113`, `domain/decode.py:28-29`) |

### Paso 3 · confirmación (`confirm`)

- La descripción muestra el host y las lecturas de la sonda (`strings.json:29`).
- `format_readings` escribe una línea por lectura, en el orden del perfil, con el nombre traducido de la entidad. Un enum muestra su estado traducido; un número, su unidad; un valor sin decodificar, `—`. Sin traducción usa la clave (`adapters/inbound/flow.py:55-70`).
- Las traducciones salen de `async_get_translations` en el idioma de HA (`adapters/inbound/flow.py:116`).
- Campo `name`. Por defecto, `"{marca} {primer modelo}"`, p. ej. `Ingeteam STORAGE 1Play TL M` (`adapters/inbound/flow.py:150-153`). Es el título de la entry y el nombre del dispositivo.

### Datos guardados

`data = {host, port, unit_id, profile, intervals}` con los intervalos por defecto (`adapters/inbound/flow.py:142-149`).

## Entries de la versión 1

Hasta `0.1.0b2` había una entry por marca con un subentry por equipo (ADR [0004](../decisions/0004-entry-brand-subentry-device.md)). El flow es ahora `VERSION = 2` (`adapters/inbound/flow.py:76`). Una entry v1 no se migra: queda en `MIGRATION_ERROR` y el log dice «Modbus Solar now uses one entry per inverter instead of one per brand. Delete this entry and add each inverter again.» (`__init__.py:47-55`). Hay que borrarla y añadir cada inversor.

## Reconfigure

Paso `reconfigure` de la entry (`adapters/inbound/flow.py:157-200`).

- Cambia `host`, `port` y los intervalos `fast`, `normal` y `slow`.
- No cambia `unit_id` ni el modelo: el formulario no los ofrece.
- No prueba el equipo.
- Recalcula el `unique_id` con el nuevo `host` y `port`. Si choca con otra entry del dominio, aborta con `already_configured` (`adapters/inbound/flow.py:167-172`).
- Guarda y recarga la entry con `async_update_reload_and_abort` (`adapters/inbound/flow.py:174-182`). La recarga abre la conexión con el endpoint nuevo.
- `interval_too_short`: un intervalo es menor que el tiempo de lectura de su tier (`adapters/inbound/flow.py:163-165`). Ese tiempo es `nº de bloques × min_request_interval_s` (`application/poller.py:46-49`).

Mínimos del STORAGE 1Play TL M: 1,0 s por petición, bloques de 10 registros como máximo y huecos de hasta 9 registros leídos dentro del bloque (`profiles/ingeteam/oneplay_storage.py:103-106`):

| Tier | Bloques (direcciones) | Mínimo |
|---|---|---|
| `fast` | 3 (15-20, 33-37, 71-78) | 3 s |
| `normal` | 3 (17-26, 31-35, 69-70) | 3 s |
| `slow` | 6 (6-7, 21-29, 38-46, 48-57, 59-60, 77-80) | 6 s |

El mínimo cuenta todas las entidades del tier, también las deshabilitadas (`application/poller.py:46-49`).

Mínimos del 1Play TL M sin storage (`min_request_interval_s=1.0`, `profiles/ingeteam/oneplay.py:12`):

| Tier | Registros | Bloques | Mínimo |
|---|---|---|---|
| `fast` | `0x101D`, `0x1037` | 2 | 2 s |
| `normal` | `0x1021` | 1 | 1 s |
| `slow` | ninguno | 0 | 1 s (mínimo del campo, `adapters/inbound/flow.py:44`) |

## Intervalos por defecto

`fast` 5 s, `normal` 60 s, `slow` 3600 s (`const.py:13`). Decisión: [ADR 0005](../decisions/0005-poll-tiers.md).
