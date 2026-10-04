# Funcionalidad: monitorización

Documento vivo. Rutas bajo `custom_components/modbus_solar/` salvo indicación. Fuente de los registros: [registers.md](../wiki/brands/ingeteam/1-play-tl-m/registers.md).

## Sensores del Ingeteam 1Play Storage

Definidos en `profiles/ingeteam/oneplay_storage.py:17-50`. Nombres en `strings.json:56-72`.

| Clave | Nombre | Tipo | Unidad | Tier | Registro | Clases de HA |
|---|---|---|---|---|---|---|
| `inverter_state` | Inverter state | enum | — | `fast` | `0x101D` (U16) | `device_class=enum` |
| `active_power` | Active power | número | W | `fast` | `0x1037` (S32, escala 0,1) | `power`, `measurement` |
| `total_energy` | Total energy | número | Wh | `normal` | `0x1021` (U32, escala 0,1) | `energy`, `total_increasing` |

Estados de `inverter_state` (`profiles/ingeteam/oneplay_storage.py:26`): `0` `factory_default`, `1` `grid_disconnected`, `3` `grid_connected`. Solo estos tres están documentados en el PDF (nota 3).

La escala `[X x 10]` y el orden de palabras de los registros de 32 bits siguen sin verificar en equipo. Se comprueban con diagnostics (ver abajo).

## Disponibilidad

- Cada tier lee todos sus registros o falla entero (spec §5). Si la lectura falla (`DeviceUnavailable` o `DeviceProtocolError`), el coordinator lanza `UpdateFailed` y las entidades del tier pasan a `unavailable` (`adapters/inbound/coordinator.py:54-58`).
- Vuelven en la siguiente lectura correcta, sin intervención. El log de pérdida (`error`) y de recuperación (`info`) lo emite `DataUpdateCoordinator`, una vez por cambio de estado y no en cada tick (`adapters/inbound/coordinator.py:57`).
- Un equipo caído al arrancar no bloquea la entry: no se lanza `ConfigEntryNotReady` y el primer refresh va en segundo plano (`__init__.py:45-48`). Las entidades nacen `unavailable` hasta su primera lectura correcta (`adapters/inbound/entities/base.py:37-39`).
- Si otro cliente ocupa el único puerto Modbus del equipo (por ejemplo, el EMS), el equipo sale `unavailable`. Ver [setup](../guides/setup.md).

## Valor fuera del enum

Un valor de `inverter_state` que no está en el enum lanza `DecodeError` (`domain/decode.py:28-29`). Solo afecta a esa entidad: su valor es `None` (`unknown`) y el resto del tier sigue en pie (`application/poller.py:37-42`). El coordinator avisa con un `warning` una sola vez por clave hasta que el valor vuelve a decodificar bien (`adapters/inbound/coordinator.py:59-63`).

## Panel de Energía

`total_energy` es la producción solar total: `device_class=energy`, `state_class=total_increasing` y unidad `Wh` (`profiles/ingeteam/oneplay_storage.py:46-48`). Se añade en el panel de Energía de HA como producción solar.

## Diagnostics

Se descarga desde HA con «Download diagnostics»: en la página del dispositivo del equipo (`diagnostics.py:22-29`) o en la de la entry de marca, que agrega todos los equipos (`diagnostics.py:13-19`). El dispositivo de marca devuelve `{}`, porque no tiene registros propios.

Por equipo (`adapters/inbound/diagnostics.py:14-43`):

- `profile` e `intervals`;
- `tiers`: `last_update_success`, `last_error` y `last_error_at` de cada tier;
- `entities`: por clave, `address`, `dtype`, `word_order`, `scale`, `raw` (palabras sin decodificar) y `value` decodificado (`adapters/inbound/diagnostics.py:30-35`);
- `subentry`: los datos del equipo con `host` oculto por `async_redact_data` (`adapters/inbound/diagnostics.py:11`, `:38`).

Uso: en la VM, comparar `raw`, `scale` y `word_order` con el valor real del equipo para verificar las escalas `[X x 10]` y el orden de palabras.
