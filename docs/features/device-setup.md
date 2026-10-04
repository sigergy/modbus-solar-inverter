# Funcionalidad: alta y configuración de equipos

Documento vivo. Rutas bajo `custom_components/modbus_solar/` salvo indicación. Los nombres de campo y de error son las claves de `strings.json`.

## Alta de la marca

- Una entry por marca, sin datos de conexión: los equipos son subentries (`adapters/inbound/flow.py:49-69`).
- Campo del formulario: `brand` (`strings.json:8`). Hoy solo existe `ingeteam` (`const.py:15`).
- Repetir la marca aborta con `already_configured` (`strings.json:13`; `adapters/inbound/flow.py:59-60`).

## Alta del equipo

Desde la entry de la marca, «Add device» (`strings.json:20`). Campos (`adapters/inbound/flow.py:104-111`):

| Campo | Valor por defecto | Rango |
|---|---|---|
| `name` | — | texto |
| `host` | — | texto |
| `port` | `profile.default_port` (502 en Ingeteam) | 1-65535 |
| `unit_id` | `profile.default_unit_id` (1 en Ingeteam) | 1-247 |
| `profile` | primer perfil de la marca | perfiles de la marca de la entry |

Rangos en `adapters/inbound/flow.py:40-42`. Los valores por defecto del Ingeteam, en `profiles/ingeteam/oneplay_storage.py:14-15`.

### Sonda

Antes de guardar, el flow abre una unit temporal y lee la entidad `probe_key` del perfil (`inverter_state`, `0x101D` en Ingeteam: `profiles/ingeteam/oneplay_storage.py:16`, `:22`) con `probe_device` (`adapters/inbound/flow.py:167-171`, `application/probe.py:8-12`). Si el equipo no responde bien, no se crea la subentry.

### Errores del formulario

| Error | Cuándo | Origen |
|---|---|---|
| `cannot_connect` | el equipo no responde | `DeviceUnavailable` (`adapters/inbound/flow.py:174-175`) |
| `endpoint_in_use` | el endpoint ya está en uso con otros parámetros de enlace | `HomeAssistantError` de `async_get_temporary_unit`, traducido a `EndpointInUse` (`config_flow.py:30-32`, `adapters/inbound/flow.py:172-173`) |
| `invalid_response` | excepción Modbus o valor fuera del enum | `DeviceProtocolError` o `DecodeError` (`adapters/inbound/flow.py:176-177`, `domain/decode.py:28-29`) |

Abort `already_configured`: mismo `host:port:unit_id`, con el host en minúsculas (`adapters/inbound/flow.py:45-46`, `:85-88`). Se comprueba antes de abrir conexión.

### Datos guardados

`data = {host, port, unit_id, profile, intervals}` con los intervalos por defecto (`adapters/inbound/flow.py:91-101`).

## Reconfigure

Paso `reconfigure` de la subentry (`adapters/inbound/flow.py:119-161`).

- Cambia `host`, `port` y los intervalos `fast`, `normal` y `slow`.
- No cambia `unit_id` ni el modelo: el formulario no los ofrece.
- Recalcula el `unique_id` con el nuevo `host` y `port`. Si choca con otro equipo de la entry, aborta con `already_configured`.
- Guarda con `async_update_and_abort`; el update listener recarga la entry de marca (`__init__.py:52`).
- `interval_too_short`: un intervalo es menor que el tiempo de lectura de su tier (`adapters/inbound/flow.py:127-128`). Ese tiempo es `nº de bloques × min_request_interval_s` (`application/poller.py:46-49`).

Mínimos del Ingeteam 1Play Storage (`min_request_interval_s=1.0`, `profiles/ingeteam/oneplay_storage.py:12`):

| Tier | Registros | Bloques | Mínimo |
|---|---|---|---|
| `fast` | `0x101D`, `0x1037` | 2 | 2 s |
| `normal` | `0x1021` | 1 | 1 s |
| `slow` | ninguno | 0 | 1 s (mínimo del campo, `adapters/inbound/flow.py:42`) |

## Intervalos por defecto

`fast` 5 s, `normal` 60 s, `slow` 3600 s (`const.py:13`). Decisión: [ADR 0005](../decisions/0005-poll-tiers.md).
