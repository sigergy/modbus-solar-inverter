# Análisis de arquitectura — integración Modbus para Home Assistant

- **Fecha:** 2026-10-03
- **Estado:** borrador de brainstorming. No hay código escrito.
- **Referencia analizada:** `sigergy/irrigation-scheduler`, commit `cddb270` (v1.1.0).
- **Repo destino:** `sigergy/modbus-solar-inverter`. GitHub lo renombró desde `ingeteam-inverter`; el remote local sigue apuntando a la URL vieja (funciona por redirección).

---

## Parte 1 — `irrigation-scheduler`: estado actual

```
custom_components/irrigation_scheduler/
  __init__.py, config_flow.py, 6 plataformas, const.py, errors.py   ← raíz exigida por HA
  domain/     model, runtime, schedule, rain, alerts, validation    ← puro
  engine/     manager, slots, triggers, rain_control, incidents, manual, status + tests/
  adapters/   store, valves, notify, speak, rain_source, registry, card_resource
  api/        websocket, services, schemas, snapshot, lookup
  entities/   base, sync, unique_ids + tests/
  frontend/irrigation-scheduler.js   ← bundle compilado y commiteado (5070 líneas)
frontend/src/  card/, panel/, shared/, api.ts, store.ts, i18n.ts     ← Lit + Vite
```

### Lo que está bien y conviene copiar

- **`domain/` no importa HA.** Comprobado con grep: no hay ningún `homeassistant` en `domain/`.
- **`ValveSlots` es puro y tiene tests** (`engine/slots.py`, `engine/tests/test_slots.py`).
- **Un único dueño del lock.** El I/O va fuera del lock, en tareas en segundo plano (`engine/manager.py:117-121`).
- **Escritura diferida al Store** con `async_delay_save` (`adapters/store.py:43-51`).
- **Frontend:** una sola suscripción por conexión, que comparten el panel y las tarjetas (`frontend/src/store.ts:5`). La caché se invalida con el hash del bundle (`__init__.py:36-43`).
- **CI** con ruff, compileall y pytest-HA (`.github/workflows/tests.yml`).

### Lo que falla frente a los 5 ejes

| Eje | Problema | Evidencia |
|---|---|---|
| Hexagonal | Las carpetas se llaman `adapters/`, pero no hay puertos. `engine/` importa HA directamente. | `engine/manager.py:13-23`, `engine/triggers.py:13-17`, `engine/rain_control.py:11-17` |
| Hexagonal | Dependencia invertida: el núcleo importa un adaptador de entrada. | `engine/manager.py:27` importa `api.snapshot` |
| Modularidad | Un adaptador depende de otro. | `adapters/registry.py:13` importa `entities.unique_ids` |
| Mantenibilidad | `manager.py` sigue siendo un god object: 966 líneas, cuando el objetivo eran 500-600. | `docs/superpowers/specs/2026-09-30-backend-restructure-design.md` §4 Fase 3 |
| Velocidad con HA | Cada `SIGNAL_STATE` repinta todas las entidades y reenvía el snapshot completo a cada cliente WS. | `entities/base.py:20-30`, `api/websocket.py:253-259` |
| Mantenibilidad | Los tests viajan dentro del paquete que se instala por HACS. El riesgo está anotado en la spec, pero sin resolver. | `engine/tests/`, `entities/tests/`; `hacs.json` no tiene `zip_release` |
| Mantenibilidad | El bundle compilado se commitea, así que hay diffs enormes y conflictos en cada build. | `custom_components/irrigation_scheduler/frontend/irrigation-scheduler.js` |
| Mantenibilidad (front) | Hay ficheros monolíticos. | `zone-editor.ts` 893 líneas, `settings-view.ts` 574, `i18n.ts` 572 |
| Tests | Los tests con HA no corren en Windows porque `lru-dict` necesita MSVC (spec §4 Fase 0). | — |

### Mejoras propuestas para `irrigation-scheduler`

1. **Puertos explícitos.** Crear `domain/ports.py` con `Protocol`s: `ValveGateway`, `RuntimeStore`, `Notifier`, `Clock`.
   - `engine/` dependería solo de esos puertos.
   - HA quedaría confinado en `adapters/`.
   - Así `engine/` se puede testear en Windows sin pytest-HA.
2. **Romper `engine → api`.** `snapshot` pasa a construirse en `api/` leyendo vistas públicas del manager.
3. **Test de capas** con `import-linter` o un test de AST, como el que ya existe para el lock: `domain` no importa nada, `engine` no importa `api`, `entities` ni `homeassistant`.
4. **Señales finas** (`SIGNAL_STATE_{zone_id}`). Cada entidad se suscribe solo a su zona. El WS manda deltas, no el snapshot entero.
5. **`tests/` en la raíz del repo, fuera del paquete.** Además, `zip_release: true` y una Action de release que compile el front. El `.js` deja de commitearse.
6. **Partir `manager.py` por casos de uso:** `commands/` (run, stop, pause) y `lifecycle/` (recover, heartbeat).

---

## Parte 2 — Integración Modbus para HACS

### Corrección de nombres

En arquitectura hexagonal, **«adapters» significa I/O**: Modbus TCP, HA, Store. Las definiciones por marca y modelo son **perfiles de dispositivo**. Usar la misma palabra para las dos cosas confunde el diseño. Por eso van en `profiles/`.

### Estructura

```
custom_components/modbus_solar/
  __init__.py  config_flow.py  manifest.json  diagnostics.py  strings.json  translations/  const.py
  sensor.py             ← fino: delega en la factoría de entidades
                          (binary_sensor, number, select, switch, button llegan en fases posteriores)
  domain/               ← solo stdlib: sin HA ni modbus_connection
    types.py            DataType, RegisterKind, PollTier, Role, Platform, WordOrder
    profile.py          RegisterSpec, EntitySpec, DeviceProfile (dataclasses frozen)
    decode.py           u16/s16/u32/s32, word order, escala, offset, enum
    errors.py           DeviceUnavailable, DeviceProtocolError, DecodeError
    validate.py         validación de perfiles
  ports/
    device.py           Protocol DeviceGateway
  application/          ← casos de uso: domain + ports; sin homeassistant ni modbus_connection
    poller.py           lee y decodifica un tier
    probe.py            prueba del equipo en el config flow
    catalog.py          perfiles por marca e id
  adapters/
    inbound/            lado HA: config flow, coordinators, entidades, diagnostics
    outbound/
      modbus_gateway.py implementa DeviceGateway sobre ModbusUnit de modbus-connection
  profiles/             ← solo domain
    ingeteam/
      oneplay_storage.py   familia 1Play Storage; variantes 3TL/6TL si comparten mapa
  frontend/             bundle (generado en release, no commiteado)
frontend/src/           TS fuente
tests/                  fuera del paquete
  unit/                 domain, application, profiles y gateway con el mock de modbus-connection
  ha/                   pytest-homeassistant-custom-component
```

**Reglas de dependencia**, verificadas con `import-linter` en CI:

- capas `adapters > application > ports > domain`;
- `domain`, `ports`, `application` y `profiles` no importan `homeassistant` ni `modbus_connection`;
- `adapters.inbound` y `adapters.outbound` son independientes. Solo las raíces de composición (`__init__.py` y `config_flow.py`) los conectan.

### Lógica compartida

- **Conexión compartida.** Cada equipo obtiene su `ModbusUnit` con `homeassistant.components.modbus.async_get_unit`, que comparte una conexión por endpoint entre varios `unit_id`. Por ejemplo, un meter colgado del RS485 del inversor por pasarela. La librería es `modbus-connection` 4.10.0, la que fija el core en HA 2026.9.0. No se usa pymodbus directo.
- **Espaciado de peticiones.** Lo aplica la librería por unit con `ModbusUnit.set_message_spacing`, con el mínimo que declara el perfil (≥ 1 s en el Ingeteam).
- **Agrupado de lecturas.** El gateway agrupa los registros contiguos en bloques y hace una lectura por bloque.
- **Coordinadores por tier de sondeo:**
  - `fast` (5 s): potencias y estado;
  - `normal` (60 s): energías y temperaturas;
  - `slow` (3600 s): número de serie, firmware, modelo.
- **Pipeline de escritura** (control, sobre el protocolo de comandos AAA0030IMB03):
  1. comprobar los límites del perfil;
  2. escribir;
  3. releer y confirmar;
  4. refrescar el coordinador;
  5. dejar constancia en el logbook.
- **Disponibilidad.** Si falla la lectura de un tier, sus entidades pasan a `unavailable` y se reintenta en el siguiente tick. No se reintenta en bucle cerrado. Un equipo caído no bloquea la entry de su marca.
- **Diagnóstico.** `diagnostics.py` muestra por entidad el raw y el valor decodificado, y por tier el último éxito y el último error. Sirve para verificar escala y word order en la VM.

### Opción a) frente a b)

**Opción b) (plantillas Modbus desde el front): no se recomienda como base.**

- **Ya existe.** El `modbus` del core de HA permite definir registros genéricos en YAML. Esta integración aporta valor justo con lo contrario: **perfiles curados, probados y con control seguro**.
- **Escribir registros arbitrarios desde una plantilla de usuario es peligroso.** Hablamos de un inversor con batería. Un error de escala o de dirección puede dejar la batería fuera de rango o hacer que el inversor se dispare.
- **Coste de UI muy alto:** editor de registros, validación de tipos, word order, escalas, enums, traducciones…
- **Traducciones.** HA nombra las entidades con `translation_key` declaradas en `strings.json`. Las plantillas dinámicas no tienen traducción ni iconos.

**Opción a), con estos ajustes:**

- **No usar `adapters/{brand}/{device_type}/{model}`.** Esos tres niveles de carpetas acaban duplicando código entre modelos de una misma familia. Mejor `profiles/{brand}/{family}.py`, con `device_type` como campo y variantes por modelo.
- **Perfil declarativo, no código.** Cada perfil es una lista de `EntitySpec`, al estilo de las `EntityDescription` de HA: registro, tipo, escala, unidad, `device_class`, `state_class`, `entity_category`, rol semántico, tier de sondeo y límites de escritura. Toda la lógica la resuelve la capa `application`, que es genérica.
- **Ganchos solo para rarezas.** Si un modelo necesita una función especial (un cálculo raro, una secuencia de escritura), se añade como función nombrada en el perfil. No hace falta una clase por modelo.
- **Esquema serializable.** Así queda abierta una **opción b) recortada** en la última fase: export/import de perfiles en JSON.

Los perfiles van **en Python**, no en YAML. Dan tipado, IDE, ruff y tests, y encajan con el estilo de HA.

### Front: alcance

El problema es que cada modelo expone un número distinto de entidades. Propuesta:

1. **No hacer tarjetas por modelo.** Escalan mal.
2. **Aprovechar lo que HA da gratis:**
   - La página de dispositivo ya agrupa las entidades en sensor / configuración / diagnóstico mediante `entity_category`.
   - El **panel de Energía** funciona sin código de front si los sensores de energía llevan `device_class: energy` y `state_class: total_increasing`. Probablemente sea lo que más valor aporta con menos coste.
3. **Tarjetas por rol semántico.** Cada `EntitySpec` declara un rol: `pv_power`, `battery_soc`, `grid_power`, `load_power`, `battery_power`, `irradiance`…
   - Las tarjetas (flujo de energía, batería, FV) piden roles, no `entity_id`.
   - El editor de la tarjeta solo pide elegir el dispositivo.
   - Si un modelo no tiene un rol, esa sección se oculta.
   - Así la misma tarjeta sirve para cualquier modelo.
4. **Una tarjeta genérica de dispositivo** que pinta los grupos que declara el perfil, por ejemplo «Red», «Batería», «FV», «Control».
5. **Panel lateral:**
   - *Ajustes generales:* marcas, equipos y control habilitado o no.
   - *Resumen:* dispositivos, estado de comunicación, alarmas activas, último error.

**Diferencia clave con irrigation:** las tarjetas leen los estados de `hass.states`, que HA ya empuja. El WS propio sirve solo para **metadatos**: rol → entity_id, grupos y límites. No hay que repetir el snapshot completo a cada cambio, porque con muchas entidades a 5 s sería un cuello de botella.

### Async y velocidad con HA

- **Sin dependencias propias.** `manifest.json` declara `dependencies: ["modbus"]` y no tiene `requirements` propios: usa `modbus-connection` tal como la fija el core en la versión mínima de HA (2026.9.0). Así no hay conflicto de versiones.
- **`DataUpdateCoordinator(always_update=False)`.** Así, si el valor no cambia, no hay escritura de estado ni recorder.
- **`CoordinatorEntity`, `_attr_should_poll = False`.** Las entidades secundarias se crean **deshabilitadas por defecto** para no llenar el recorder.
- **Timeouts en cada petición.** Las tareas se crean con `entry.async_create_background_task` y se cancelan al descargar.
- **Coalescer escrituras.** Si una automatización manda diez cambios seguidos de consigna, se escribe solo el último.

### Config flow

- **Config entry = marca (hub).** El paso `user` elige la marca del catálogo. No guarda datos de conexión.
- **Config subentry = equipo.** Campos: nombre, `host`, `port`, `unit_id` y perfil (filtrado por la marca). Antes de crearla se prueba el equipo leyendo un registro del perfil. Errores del formulario: `cannot_connect`, `invalid_response`, `endpoint_in_use`.
- Cada equipo es un dispositivo que cuelga del dispositivo de la marca con `via_device`.
- **Intervalos de sondeo** por tier (`fast` / `normal` / `slow`, por defecto 5/60/3600 s), editables en el paso `reconfigure` de la subentry junto con `host` y `port`. Cada intervalo respeta el mínimo del perfil. Las subentries no tienen options flow.

### Seguridad del control

- **El control va deshabilitado por defecto en cada dispositivo** y se activa de forma explícita.
- Límites `min`/`max`/`step` en el perfil. Fuera de rango, `ServiceValidationError`.
- **Memoria no volátil.** Hay inversores que guardan las consignas en EEPROM, y las escrituras frecuentes desde automatizaciones la desgastan. Hay que comprobarlo en el manual de Ingeteam registro a registro y, si aplica, limitar la frecuencia.

### Tests

- Todos los tests se ejecutan **solo en GitHub Actions**, nunca en Windows.
- Sin simulador pymodbus: se usa el mock en memoria de `modbus-connection` (`mock_modbus_unit`).
- `tests/unit` y `tests/ha` viven en la raíz del repo, fuera del paquete que instala HACS.

### Alcance realista por fases

0. **Esqueleto.** Capas hexagonales, config flow (marca + equipo), sondeo por tiers, diagnostics, CI y empaquetado HACS, probado de punta a punta con 3 registros del 1Play Storage.
1. **Lectura completa Ingeteam.** Resto de registros, MPPT, strings y eventos.
2. **Control.** `number`, `select`, `switch` con pipeline de escritura y guardas, mediante el protocolo de comandos AAA0030IMB03.
3. **Más dispositivos.** Meter y célula de irradiancia; perfil **SunSpec** genérico con autodescubrimiento.
4. **Front.** Tarjetas por rol, tarjeta genérica de dispositivo y panel lateral.
5. **Perfiles JSON.** Export/import de perfiles (última fase).

Los sensores derivados (`calc`: eficiencia, potencia neta, energía integrada…) quedan como fase futura, sin spec asignada.
