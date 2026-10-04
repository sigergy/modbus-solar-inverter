---
type: feature
area: config-flow
layers: [application, adapters]
status: done
date: 2026-10-04
---

# Spec 2 — Flujo de alta: una entry por inversor

## 1. Objetivo y alcance

El flujo actual tiene dos niveles (ADR 0004): una entry por marca y un subentry por equipo.
En la VM el usuario no lo encontró intuitivo:

- Tras elegir la marca, la entry se crea sin pedir modelo ni IP. No hay sensores hasta añadir
  un equipo desde la entry (`adapters/inbound/flow.py:56-64`).
- «Añadir equipo» se queda cargando sin fin. La causa no se conoce: no hay logs.
- El modelo va al final del formulario y ya viene elegido (`adapters/inbound/flow.py:103-110`).

Esta spec aplica la **opción A** del mockup [setup-flow-proposal.html](setup-flow-proposal.html):
un alta, un inversor. Decisión: [ADR 0010](../../decisions/0010-entry-per-device.md), que
sustituye al ADR 0004.

**Dentro:**
- Una config entry por inversor. Se quitan la entry de marca, su dispositivo y los subentries.
- Flujo en tres pasos: modelo → conexión → confirmación con lecturas reales.
- Tiempo máximo para la sonda.
- Reconfigure de la entry: host, puerto e intervalos.
- `integration_type: device`.
- Entries v1: no se migran (§6).

**Fuera:**
- Botón «Atrás» en el flujo: HA no lo ofrece en config flows.
- Interpretar el signo de las lecturas con texto («exportando», «descargando»): los signos no
  están verificados (`docs/features/monitoring.md`, «Signos supuestos»).
- Comprobar que el modelo elegido es el real. Los dos perfiles Ingeteam leen `inverter_state`
  con mapas distintos y no hay un registro de modelo fiable.
- Descubrimiento automático (DHCP, zeroconf).

## 2. Modelo de datos

Una `ConfigEntry` por inversor, `VERSION = 2`.

| Campo | Valor |
|---|---|
| `title` | nombre que da el usuario en el paso 3 |
| `unique_id` | `device_unique_id(host, port, unit_id)` = `"{host.lower()}:{port}:{unit_id}"` (`adapters/inbound/flow.py:45-46`, sin cambios) |
| `data` | `host`, `port`, `unit_id`, `profile`, `intervals` (las mismas claves que el subentry) |

El `entry_id` sustituye al `subentry_id` en todo lo que lo usaba:

- `unique_id` de entidad: `f"{entry_id}_{key}"`. Cambiar el host sigue sin duplicar entidades.
- identificador del dispositivo: `(DOMAIN, entry_id)`.

No hay dispositivo de marca ni `via_device`. Se quitan `CONF_BRAND` y `SUBENTRY_DEVICE` de
`const.py`.

## 3. Flujo de alta

Clase `DeviceConfigFlow(ConfigFlow)` en `adapters/inbound/flow.py`. `config_flow.py` le inyecta
`catalog` y `gateway_factory`, como hoy (`config_flow.py:36-43`).

### Paso 1 · `user` — modelo

- Campo `profile`: `SelectSelector` en modo `list`, sin valor por defecto.
- Una opción por perfil del catálogo, por marca (`catalog.brands()`) y dentro por id
  (`catalog.for_brand()`).
- Etiqueta: `"{marca} · {modelos}"`, p. ej. `Ingeteam · STORAGE 1Play TL M`.

### Paso 2 · `connection` — conexión

- `host`: obligatorio.
- Sección `advanced`, plegada: `port` y `unit_id`, con los valores por defecto del perfil
  (`default_port`, `default_unit_id`).
- Al enviar:
  1. `async_set_unique_id(device_unique_id(...))` y `_abort_if_unique_id_configured()`.
     El duplicado aborta con `already_configured` antes de abrir conexión.
  2. Sonda (§4), con un tiempo máximo de `PROBE_TIMEOUT_S = 20` s.
- Errores del formulario:

| Causa | Clave |
|---|---|
| Endpoint en uso con otros parámetros (`EndpointInUse`) | `endpoint_in_use` |
| Sin respuesta (`DeviceUnavailable`) o tiempo máximo agotado | `cannot_connect` |
| Respuesta Modbus de error o valor fuera del enum (`DeviceProtocolError`, `DecodeError`) | `invalid_response` |

Con error, el formulario se vuelve a mostrar con lo que escribió el usuario.

### Paso 3 · `confirm` — lecturas reales

- La descripción muestra el host y las lecturas de la sonda: una línea por clave, con el nombre
  traducido de la entidad y su valor con unidad. Un enum muestra su estado traducido. Un valor
  sin decodificar muestra `—`.
- Traducciones: `async_get_translations(hass, hass.config.language, "entity", {DOMAIN})`, claves
  `component.modbus_solar.entity.sensor.<key>.name` y `….state.<valor>`. Sin traducción, la
  clave.
- Campo `name`, obligatorio. Por defecto: `"{marca} {primer modelo}"`.
- Al enviar: `async_create_entry(title=name, data=…)` con `intervals = DEFAULT_INTERVALS`.

### Diferencias con el mockup

- Sin botón «Atrás».
- Sin texto de signo («exportando 300 W»): se muestra el valor con su signo.
- Sin aviso de «el modelo no cuadra».

## 4. Sonda

`probe_device(gateway, profile) -> TierResult` (`application/probe.py`):

1. Lee y decodifica `probe_key`, como hoy. Un valor inválido lanza `DecodeError`.
2. Lee el tier `fast` con `read_tier`, limitado a las entidades `enabled_default`.
3. Devuelve ese `TierResult`.

Para los dos perfiles Ingeteam `probe_key` es `inverter_state`, del tier `fast`.

## 5. Reconfigure

`async_step_reconfigure` de la entry, con los mismos campos y validaciones que el reconfigure
del subentry (`adapters/inbound/flow.py:119-161`):

- `host`, `port` y los tres intervalos.
- Un intervalo menor que `min_tier_interval` da `interval_too_short` en su campo.
- Si otra entry del dominio ya tiene el nuevo `unique_id`, aborta con `already_configured`.
- Si no, `async_update_reload_and_abort(entry, unique_id=…, data_updates=…)`. Termina con
  `reconfigure_successful` y recarga la entry.
- Sin sonda, como hoy.

Se quita el update listener de `__init__.py:52`. `async_update_reload_and_abort` ya recarga, y
con listener HA avisa de un uso que deja de funcionar en 2026.12.0
(`homeassistant/config_entries.py:3547`).

## 6. Entries v1

No se migran. `async_migrate_entry` registra un error y devuelve `False` para `version == 1`.
HA deja la entry en `MIGRATION_ERROR` (`homeassistant/config_entries.py:1150-1209`). El usuario
la borra y vuelve a añadir cada inversor.

El error dice: `Modbus Solar now uses one entry per inverter instead of one per brand. Delete
this entry and add each inverter again.`

Hay muy pocas instalaciones, todas betas de prueba. Migrar exigiría partir una entry en varias.

## 7. Resto de piezas

| Pieza | Cambio |
|---|---|
| `__init__.py` | Un `DeviceRuntime` por entry. Sin dispositivo de marca ni update listener. Añade `async_migrate_entry`. |
| `adapters/inbound/runtime.py` | `DeviceRuntime.entry_id`. `ModbusSolarConfigEntry = ConfigEntry[DeviceRuntime]`. `build_runtime(hass, entry, profile, gateway, keys)` |
| `adapters/inbound/entities/*` | Sin `brand_device_id`. Dispositivo `(DOMAIN, entry_id)` |
| `sensor.py` | `async_add_entities(build_sensors(entry.runtime_data))` |
| `diagnostics.py` | Entry y dispositivo devuelven lo mismo. La clave `subentry` pasa a `entry` |
| `manifest.json` | `"integration_type": "device"` |
| `strings.json`, `translations/` | Pasos `user`, `connection`, `confirm` y `reconfigure` en `config`. Se quita `config_subentries` |

## 8. Criterios de aceptación

- El alta de un STORAGE pide modelo, IP y nombre, y crea sensores sin pasos extra.
- El mismo host, puerto y unit ID no se añade dos veces.
- Un inversor que no responde da `cannot_connect` en 20 s como máximo.
- El paso 3 muestra lecturas reales traducidas.
- El reconfigure cambia host, puerto e intervalos y recarga.
- Una entry v1 queda en `MIGRATION_ERROR` con el mensaje de §6.
- Tests y lint en verde en CI.

## 9. Pendiente de verificar en la VM

- Texto del botón de alta con `integration_type: device`.
- Que la carga infinita del subentry flow no se repite en el flujo nuevo.
