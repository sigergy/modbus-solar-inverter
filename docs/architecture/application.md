# Arquitectura: application

Documento vivo. Funciones de caso de uso. Importa `domain` y `ports`; no importa `homeassistant`, `modbus_connection` ni `profiles` (`pyproject.toml:35-44`, `:52-56`). Rutas bajo `custom_components/modbus_solar/application/`.

## `Catalog` (`catalog.py:8-23`)

Perfiles por marca e id. No conoce perfiles concretos: se los inyecta la raíz (`catalog.py:1`, `custom_components/modbus_solar/__init__.py:17`).

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

## `min_tier_interval` (`poller.py:46-49`)

`min_tier_interval(profile, tier) -> float`: segundos mínimos para leer el tier entero respetando el espaciado entre peticiones. Es `len(plan_blocks(registros, profile.max_gap, profile.max_block_registers)) * profile.min_request_interval_s` (`poller.py:49`): agrupa igual que el gateway. No lanza errores propios. Lo usa el reconfigure para rechazar intervalos demasiado cortos (`custom_components/modbus_solar/adapters/inbound/flow.py:164`).

## `probe_device` (`probe.py:10-17`)

`async probe_device(gateway, profile) -> TierResult`: valida que el equipo responde y devuelve lecturas para el paso de confirmación del config flow.

1. Lee la entidad `profile.probe_key` con el gateway y la decodifica (`probe.py:11-14`).
2. Lee el tier `fast` con `read_tier`, limitado a las entidades `enabled_default`, y devuelve su `TierResult` (`probe.py:16-17`).

Errores:

- `DeviceUnavailable` y `DeviceProtocolError` se propagan desde `gateway.read`, en los dos pasos (`probe.py:12`, `:17`).
- `DecodeError` se propaga si el valor no es válido, por ejemplo fuera del `enum` (`probe.py:13-14`). En el paso 2, como en `read_tier`, un `DecodeError` queda en `decode_errors` y el valor en `None`.
- Si `probe_key` no existe en el perfil, el `next(...)` sin valor por defecto falla sin gestionar (`probe.py:11`). `validate_profile` lo detecta antes (`custom_components/modbus_solar/domain/validate.py:22-23`).

El config flow traduce estos errores a claves de formulario (ver [inbound](adapters/inbound.md)).
