# Arquitectura: application

Documento vivo. Funciones de caso de uso. Importa `domain` y `ports`; no importa `homeassistant`, `modbus_connection` ni `profiles` (`pyproject.toml:35-44`, `:52-56`). Rutas bajo `custom_components/modbus_solar/application/`.

## `Catalog` (`catalog.py:8-23`)

Perfiles por marca e id. No conoce perfiles concretos: se los inyecta la raíz (`catalog.py:1`, `custom_components/modbus_solar/__init__.py:20`).

| Método | Devuelve | Errores | Cita |
|---|---|---|---|
| `Catalog(profiles)` | construye el índice por `profile.id` | `ValueError` si un `id` se repite | `catalog.py:9-14` |
| `brands()` | marcas, ordenadas, sin repetir | — | `catalog.py:16-17` |
| `for_brand(brand)` | perfiles de la marca, ordenados por `id` | — | `catalog.py:19-20` |
| `get(profile_id)` | el perfil | `KeyError` si no existe | `catalog.py:22-23` |

## `read_tier` y `TierResult` (`poller.py`)

`TierResult` (`poller.py:14-18`): `dataclass` inmutable con tres diccionarios por clave de entidad.

- `values`: valor decodificado, o `None` si falló la decodificación.
- `raw`: palabras crudas.
- `decode_errors`: mensaje del `DecodeError`.

`async read_tier(tier, gateway, profile, keys) -> TierResult` (`poller.py:21-43`):

1. Selecciona las entidades del tier cuya clave está en `keys` (`poller.py:28`). Las deshabilitadas no se leen.
2. Sin entidades devuelve un `TierResult` vacío y no llama al gateway (`poller.py:29-30`).
3. Una sola llamada `gateway.read` con todos los registros (`poller.py:31`).
4. Decodifica cada entidad (`poller.py:35-38`).

Errores:

- `DeviceUnavailable` y `DeviceProtocolError` **se propagan** sin tocar: vienen del gateway (`poller.py:31`) y las gestiona el `TierCoordinator` (`custom_components/modbus_solar/adapters/inbound/coordinator.py:54-60`).
- `DecodeError` **se captura por entidad**: su valor queda en `None` y el mensaje en `decode_errors`, sin abortar el tier (`poller.py:39-42`).

## `min_tier_interval` y `request_rate` (`poller.py:46-54`)

`min_tier_interval(profile, tier) -> float`: segundos mínimos para leer el tier entero respetando el espaciado entre peticiones. Es `len(plan_blocks(registros, profile.max_gap, profile.max_block_registers)) * profile.min_request_interval_s` (`poller.py:49`): agrupa igual que el gateway. Cuenta todas las entidades del perfil en el tier, no solo las de la selección (`poller.py:48`). No lanza errores propios. Lo usa el flujo de intervalos para rechazar intervalos demasiado cortos (`custom_components/modbus_solar/adapters/inbound/flow.py:226-227`).

`request_rate(profile, intervals) -> float`: peticiones por segundo que piden los tiers con esos intervalos, la suma de `min_tier_interval / intervalo` (`poller.py:52-54`). El equipo admite 1; el flujo rechaza lo que pase de ahí con `interval_budget_exceeded` (`custom_components/modbus_solar/adapters/inbound/flow.py:229-230`). ADR [0016](../decisions/0016-instant-tier.md).

## `Selection` y `select` (`selection.py`)

`Selection` (`selection.py:12-16`): `dataclass` inmutable con las `entities`, `energies` y `controls` de los componentes elegidos.

`select(profile, components) -> Selection` (`selection.py:19-27`): filtra por `component`. El componente `main` siempre entra (`selection.py:22`). `components=None` equivale a todos los opcionales del perfil: así se tratan las entries anteriores a v2, que no guardan la clave (`selection.py:20-21`). La usan el flujo, `build_runtime`, la raíz y diagnostics.

## `set_limit` y `set_enabled` (`control.py`)

Casos de uso de un control del equipo, el límite de vertido. Escriben primero y cambian el estado después: si `writer.write` falla, el `GatedState` no cambia (`control.py:1`).

`async set_limit(writer, spec, state, value) -> None` (`control.py:9-15`):

1. Lanza `ValueError` si `value` queda fuera de `[min_value, max_value]` (`control.py:10-11`).
2. Con el switch activo escribe el límite nuevo (`control.py:13-14`). Con el switch apagado el equipo sigue en `off_value`: el límite solo se guarda para cuando se vuelva a activar (`control.py:12`).
3. Guarda `state.limit` (`control.py:15`).

`async set_enabled(writer, spec, state, enabled) -> None` (`control.py:18-20`): escribe lo que el equipo debe tener con el nuevo `enabled`, es decir, `limit` si se activa u `off_value` si se apaga (`control.py:19`, `GatedState.effective` en `custom_components/modbus_solar/domain/control.py:41-43`). Después guarda `state.enabled` (`control.py:20`).

Errores: `EncodeError`, `DeviceUnavailable` y `DeviceProtocolError` se propagan desde `writer.write` (`custom_components/modbus_solar/ports/device.py:20`). Los traduce la entidad con `write_errors` (`custom_components/modbus_solar/adapters/inbound/entities/control.py:16-24`). El `ValueError` del rango no pasa por `write_errors`.

## `probe_device` (`probe.py:19-43`)

`async probe_device(gateway, profile) -> ProbeResult`: valida que el equipo responde y devuelve lo que necesita el config flow. `ProbeResult` (`probe.py:13-16`) es un `dataclass` inmutable con `readings` (`TierResult` de `fast` más `instant`) y `serial` (`str | None`).

1. Lee la entidad `profile.probe_key` con el gateway y la decodifica (`probe.py:20-23`).
2. Lee los tiers `fast` e `instant` con `read_tier`, limitados a las entidades `enabled_default`, y los une en `readings` (`probe.py:24-31`). La sonda lee todas las entidades del perfil: aún no hay componentes elegidos.
3. Si el perfil declara `serial`, lo lee y lo decodifica con `decode_text` (`probe.py:35-43`). Un fallo de lectura o de decodificación deja `serial=None` sin invalidar la sonda (`probe.py:41-43`).

Errores:

- `DeviceUnavailable` y `DeviceProtocolError` se propagan desde `gateway.read` en la lectura de `probe_key` y de los tiers (`probe.py:21`, `:25-26`). La del número de serie se captura (`probe.py:41-43`).
- `DecodeError` se propaga si el valor de `probe_key` no es válido, por ejemplo fuera del `enum` (`probe.py:22-23`). En los tiers, como en `read_tier`, un `DecodeError` queda en `decode_errors` y el valor en `None`.
- Si `probe_key` no existe en el perfil, el `next(...)` sin valor por defecto falla sin gestionar (`probe.py:20`). `validate_profile` lo detecta antes (`custom_components/modbus_solar/domain/validate.py:77-78`).

El config flow traduce estos errores a claves de formulario (ver [inbound](adapters/inbound.md)).
