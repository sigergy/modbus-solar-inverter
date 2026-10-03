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

En arquitectura hexagonal, **«adapters» significa I/O**: Modbus TCP, HA, Store. Las definiciones por marca y modelo son **perfiles de dispositivo**. Usar la misma palabra para las dos cosas confunde el diseño. Propuesta: llamarlos `profiles/`.

### Estructura propuesta

```
custom_components/<domain>/
  __init__.py  config_flow.py  manifest.json  diagnostics.py  strings.json  translations/
  sensor.py binary_sensor.py number.py select.py switch.py button.py   ← finos: delegan en factoría
  core/                 ← PURO: sin HA, sin pymodbus. Testeable en Windows.
    profile.py          RegisterSpec, EntitySpec, DeviceProfile (dataclasses frozen)
    codec.py            decode/encode: u16/s16/u32/s32/f32, word/byte order, escala, valores centinela
    planner.py          agrupa registros contiguos en lecturas de ≤125 registros
    calc.py             sensores derivados (eficiencia, potencia neta, energía integrada…)
    enums.py            código de estado → clave de traducción
    ports.py            Protocol ModbusPort, Clock
  engine/               ← orquestación async. Depende de core + ports.
    hub.py              una conexión por host:port, cola de peticiones, lock, backoff, reconexión
    poller.py           coordinadores por nivel de frecuencia
    commands.py         escritura: valida rango → escribe → relee → confirma
    profiles.py         registro, carga y validación de perfiles
  adapters/
    modbus_tcp.py       implementa ModbusPort con pymodbus async
    entities/           base CoordinatorEntity + factoría EntitySpec → entidad HA
    websocket.py        metadatos para el front (no estados)
  profiles/
    ingeteam/
      oneplay_storage.py   familia 1Play Storage; variantes 3TL/6TL si comparten mapa
  frontend/             bundle (generado en release, no commiteado)
frontend/src/           TS fuente
tests/
  unit/                 core/ sin HA
  ha/                   pytest-homeassistant-custom-component
  fixtures/dumps/       volcados reales de registros por modelo
```

### Qué va en `engine` (lógica compartida)

- **Hub de conexión.** Una sola conexión TCP por `host:port`, compartida entre varios `unit_id`. Por ejemplo, un meter colgado del RS485 del inversor por pasarela. Las peticiones se serializan con un lock.
- **Planificador de lecturas.** Usa el `planner` de `core`. Solo lee los registros de **entidades habilitadas**, y así reduce el tráfico.
- **Coordinadores por nivel de frecuencia:**
  - rápido (5-10 s): potencias;
  - medio (30-60 s): energías y temperaturas;
  - estático (al arrancar y cada hora): número de serie, firmware, modelo.
- **Pipeline de escritura:**
  1. comprobar los límites del perfil;
  2. escribir;
  3. releer y confirmar;
  4. refrescar el coordinador;
  5. dejar constancia en el logbook.
- **Disponibilidad y backoff.** Tras N fallos el dispositivo pasa a `unavailable`. No se reintenta en bucle cerrado.
- **Diagnóstico.** Estadísticas de comunicación (latencia, errores, timeouts) y `diagnostics.py` con un volcado de registros. Ese volcado sirve después como fixture de tests.

### Opción a) frente a b)

**Opción b) (plantillas Modbus desde el front): no se recomienda como base.**

- **Ya existe.** El `modbus` del core de HA permite definir registros genéricos en YAML. Esta integración aporta valor justo con lo contrario: **perfiles curados, probados y con control seguro**.
- **Escribir registros arbitrarios desde una plantilla de usuario es peligroso.** Hablamos de un inversor con batería. Un error de escala o de dirección puede dejar la batería fuera de rango o hacer que el inversor se dispare.
- **Coste de UI muy alto:** editor de registros, validación de tipos, word order, escalas, enums, traducciones…
- **Traducciones.** HA nombra las entidades con `translation_key` declaradas en `strings.json`. Las plantillas dinámicas no tienen traducción ni iconos.

**Opción a), con estos ajustes:**

- **No usar `adapters/{brand}/{device_type}/{model}`.** Esos tres niveles de carpetas acaban duplicando código entre modelos de una misma familia. Mejor `profiles/{brand}/{family}.py`, con `device_type` como campo y variantes por modelo.
- **Perfil declarativo, no código.** Cada perfil es una lista de `EntitySpec`, al estilo de las `EntityDescription` de HA: registro, tipo, escala, unidad, `device_class`, `state_class`, `entity_category`, rol semántico y límites de escritura. Toda la lógica la resuelve el engine genérico.
- **Ganchos solo para rarezas.** Si un modelo necesita una función especial (un cálculo raro, una secuencia de escritura), se añade como función nombrada en el perfil. No hace falta una clase por modelo.
- **Esquema serializable.** Así queda abierta una **opción b) recortada** en una fase muy posterior: «importar perfil JSON», **solo lectura y sin escrituras**.

Se recomiendan perfiles **en Python** frente a YAML. Dan tipado, IDE, ruff y tests, y encajan con el estilo de HA.

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
   - *Ajustes generales:* conexiones (hubs), intervalos de sondeo, control habilitado o no.
   - *Resumen:* dispositivos, estado de comunicación, alarmas activas, último error.

**Diferencia clave con irrigation:** las tarjetas leen los estados de `hass.states`, que HA ya empuja. El WS propio sirve solo para **metadatos**: rol → entity_id, grupos y límites. No hay que repetir el snapshot completo a cada cambio, porque con muchas entidades a 5 s sería un cuello de botella.

### Async y velocidad con HA

- **pymodbus asíncrono.** En `manifest.json` hay que fijar la misma versión de `pymodbus` que exige la integración `modbus` del core en la versión de HA objetivo. Si no coinciden, hay conflicto de dependencias. **Pendiente de verificar antes de fijarla.**
- **`DataUpdateCoordinator(always_update=False)`.** Así, si el valor no cambia, no hay escritura de estado ni recorder.
- **`CoordinatorEntity`, `_attr_should_poll = False`.** Las entidades secundarias se crean **deshabilitadas por defecto**: no se leen ni llenan el recorder.
- **Timeouts en cada petición.** Las tareas se crean con `entry.async_create_background_task` y se cancelan al descargar.
- **Coalescer escrituras.** Si una automatización manda diez cambios seguidos de consigna, se escribe solo el último.

### Config flow

- Pasos del flujo:
  1. `host`, `port`, `unit_id`;
  2. prueba de conexión;
  3. elegir el perfil, o autodetectarlo si el modelo expone un registro de identificación;
  4. crear la entry.
- **Una entry por conexión física.** Los equipos detrás de ella (meter, célula de irradiancia) van como dispositivos hijos con `via_device`.
- Valorar *config subentries* para añadir dispositivos a un hub existente. Hay que verificar que lo soporta la versión mínima de HA que se fije.
- Options flow para intervalos y para habilitar el control.

### Seguridad del control

- **El control va deshabilitado por defecto en cada dispositivo** y se activa de forma explícita.
- Límites `min`/`max`/`step` en el perfil. Fuera de rango, `ServiceValidationError`.
- **Memoria no volátil.** Hay inversores que guardan las consignas en EEPROM, y las escrituras frecuentes desde automatizaciones la desgastan. Hay que comprobarlo en el manual de Ingeteam registro a registro y, si aplica, limitar la frecuencia.

### Alcance realista por fases

1. **MVP solo lectura.** Hub, coordinator, perfil 1Play Storage 6TL, sensores, panel de Energía y diagnostics. Tests con volcados reales y simulador pymodbus en CI.
2. **Control.** `number`, `select`, `switch` con pipeline de escritura y guardas.
3. **Más dispositivos.** Meter y célula de irradiancia. Valorar un perfil **SunSpec** genérico con autodescubrimiento, porque muchos inversores y meters lo implementan. Habría que confirmar si Ingeteam lo soporta.
4. **Front.** Tarjetas por rol, tarjeta genérica de dispositivo, panel.
5. *(Opcional)* Importar perfiles JSON de solo lectura.

---

## Preguntas abiertas

1. **Mapa Modbus oficial del Ingeteam 1Play Storage 6TL** (PDF o ruta). No se define ningún registro sin él.
2. **`domain` de la integración**, por ejemplo `modbus_solar`. No se puede cambiar después sin romper los `unique_id`.
3. **Versión mínima de HA.** irrigation usa `2026.9.0` (`hacs.json:3`).
4. **Ruta para specs y planes** de las fases siguientes.
