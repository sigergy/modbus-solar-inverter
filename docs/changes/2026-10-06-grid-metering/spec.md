---
type: feature
area: energy
layers: [domain, application, adapters]
status: done
date: 2026-10-06
refs:
  - decisions/0002-python-profiles.md
  - decisions/0009-computed-energy.md
  - decisions/0015-device-per-component.md
docs:
  - features/device-setup.md
  - features/monitoring.md
  - architecture/domain.md
  - architecture/application.md
  - architecture/adapters/inbound.md
---

# Spec — Medición de red: potencia importada, exportada y generador en el STORAGE 1Play TL M

Rutas bajo `custom_components/modbus_solar/` salvo indicación.

## 1. Objetivo y alcance

El STORAGE 1Play TL M es un inversor híbrido. Según la instalación, el intercambio con la red lo mide un
vatímetro u otro (`ABH2014IQM01`, apdo. 19.8, pág. 60):

- **Autoconsumo con vatímetro externo** en el punto de conexión. Hay cargas en la red y en la salida de cargas
  críticas. El vatímetro externo mide el intercambio: registro 30072.
- **Autoconsumo o SAI sin vatímetro externo.** El manual exige que todas las cargas estén en la salida de cargas
  críticas. Las bornas de red del inversor son el único punto de conexión, y el vatímetro interno (30052) mide el
  intercambio.
- **Aislada.** Se usa el vatímetro interno y todas las cargas van en cargas críticas. Las bornas de red pueden
  llevar un grupo electrógeno: el manual llama a esa entrada «grid/genset» (apdo. 10.3).

Hoy la integración solo lee la red del vatímetro externo (`profiles/ingeteam/oneplay_storage.py:261`, `:271-273`).
Las energías importada y exportada integran siempre 30072 (`profiles/ingeteam/oneplay_storage.py:411-424`). En
una instalación sin vatímetro externo esas energías son falsas.

**Dentro:**

- Desplegable «Medición de red» en el alta y en reconfigurar, solo para los perfiles que lo declaran. Hoy, el
  STORAGE 1Play TL M.
- Concepto nuevo de dominio: **potencia derivada**, que es una potencia leída con filtro de signo.
- Dos potencias derivadas nuevas: «Potencia de red» (importada) y «Potencia a la red» (exportada).
- Las energías importada y exportada pasan a integrar esas potencias, con la fuente que diga el desplegable.
- Modo aislado: dispositivo nuevo «Generador», con su potencia y su energía.

**Fuera:**

- Detección automática del vatímetro. No hay registro que la dé (§2), y el usuario eligió opción manual.
- Verificar los signos de 30072 y 30052. Se hace en la VM (§9).
- Configurar el panel de Energía de HA.
- El perfil 1Play TL M sin batería (`profiles/ingeteam/oneplay.py`): no declara modos y no cambia.

## 2. Hechos de partida

| Hecho | Fuente |
|---|---|
| La red se lee del vatímetro externo, 30072, S16, W, tier `instant` | `profiles/ingeteam/oneplay_storage.py:271-273` |
| El vatímetro interno se lee en 30052, S16, W, tier `fast` | `profiles/ingeteam/oneplay_storage.py:356-364` |
| El componente Vatímetro interno sale desmarcado por defecto | `profiles/ingeteam/oneplay_storage.py:189` |
| Las energías de red cuelgan de `Component.GRID` e integran `grid_power` | `profiles/ingeteam/oneplay_storage.py:411-424` |
| Signo supuesto de 30072: > 0 importa | `docs/changes/2026-10-04-storage-profile/spec.md` §3.5 |
| El signo de 30052 no está documentado ni supuesto | `ABH2010IMB08` |
| No hay registro que diga qué vatímetro usa el equipo. CMD 18 «Self-Consumption to CG Wattmeter» es de escritura | `ABH2010IMB08`; `AAA0030IMB03_N` |
| Una energía solo admite como fuentes sensores de potencia leídos, del mismo tier | `domain/validate.py:80-96` |
| `select` filtra por componente; el principal va siempre | `application/selection.py:230-243` |
| Desmarcar un componente borra sus entidades y su dispositivo | `__init__.py:28-53` |
| El paso de componentes solo sale si el perfil los declara | `adapters/inbound/flow.py:398-401`, `:623-626` |

## 3. Decisiones

| Tema | Decisión |
|---|---|
| Cómo se elige la fuente | Manual: un desplegable. Sin sugerencia automática |
| Número de desplegables | Uno. El modo decide la fuente, las entidades y el dispositivo |
| Dispositivo de las entidades | El del vatímetro que las mide: Red con el externo y Vatímetro interno con el interno. En aislada, Generador |
| Componente del vatímetro elegido | Forzado: sale marcado en «Componentes», y desmarcarlo da error |
| Energías existentes | `grid_import_energy` y `grid_export_energy` conservan clave y `unique_id`. Cambian su fuente y su dispositivo. El historial se conserva |
| Cálculo de las energías | Integran las potencias derivadas nuevas (§5.3) |
| Aislada | Crea el dispositivo Generador con su potencia y su energía. Sin grupo, marcan 0 |
| Dispositivo Generador | Lo decide el desplegable, no una casilla |
| Modo por defecto | «Consumos en Grid», el comportamiento de hoy |
| Entries ya creadas | Sin modo guardado, toman «Consumos en Grid» |

## 4. Modos de medición

| Clave | Etiqueta (es) | Etiqueta (en) | Fuente | Componente forzado | Entidades | Dispositivo |
|---|---|---|---|---|---|---|
| `grid_loads` (por defecto) | Consumos en Grid | Loads on Grid | `grid_power` (30072) | Red | Potencia de red, Potencia a la red, Energía importada, Energía exportada | Red |
| `critical_loads` | Consumos en Cargas Críticas | Loads on Critical Loads | `internal_meter_power` (30052) | Vatímetro interno | las mismas 4 | Vatímetro interno |
| `off_grid` | Aislada | Off-grid | `internal_meter_power` (30052) | Vatímetro interno | Potencia del generador, Energía del generador | Generador |

Entidades:

| Clave | Nombre (es) | Nombre (en) | Signo | Rol |
|---|---|---|---|---|
| `grid_import_power` | Potencia de red | Grid import power | positivo | `grid_import_power` (nuevo) |
| `grid_export_power` | Potencia a la red | Grid export power | negativo, en valor absoluto | `grid_export_power` (nuevo) |
| `grid_import_energy` | Energía importada (sin cambio) | — | positivo | `energy_grid_import` |
| `grid_export_energy` | Energía exportada (sin cambio) | — | negativo, en valor absoluto | `energy_grid_export` |
| `generator_power` | Potencia del generador | Generator power | positivo | `generator_power` (nuevo) |
| `generator_energy` | Energía del generador | Generator energy | positivo | `energy_generator` (nuevo) |

- Signo de 30052 **supuesto**: > 0 significa que entra potencia por las bornas de red, igual que el supuesto de
  30072. Se verifica en la VM (§9). Si el equipo dice otra cosa, se invierte el filtro en el perfil.
- Las potencias derivadas son sensores `power`, en W, con `state_class="measurement"`. Salen activadas y sin
  categoría.
- Cada entidad usa el tier de su fuente: `instant` con 30072 y `fast` con 30052.

## 5. Dominio

### 5.1 Tipos nuevos

`domain/metering.py`:

```python
@dataclass(frozen=True, kw_only=True)
class FlowSpec:
    """Un sentido del intercambio: su potencia derivada y la energía que la integra."""

    power_key: str
    power_role: Role
    energy_key: str
    energy_role: Role
    sign: SignFilter


@dataclass(frozen=True, kw_only=True)
class MeteringModeSpec:
    key: str  # valor guardado en la entry y clave de traducción
    source: str  # clave de la entidad de potencia leída (W)
    component: Component  # dispositivo de las entidades del modo
    flows: tuple[FlowSpec, ...]


@dataclass(frozen=True, kw_only=True)
class DerivedPowerSpec:
    key: str
    role: Role
    source: str
    sign: SignFilter
    component: Component
    enabled_default: bool = True
```

- `DeviceProfile.metering_modes: tuple[MeteringModeSpec, ...] = ()`. El primero es el modo por defecto.
- `Component.GENERATOR = "generator"`.
- `Role` gana `grid_import_power`, `grid_export_power`, `generator_power` y `energy_generator`.

### 5.2 Filtro de signo compartido

Función pura `filter_power(power_w: float, sign: SignFilter) -> float` en `domain/energy.py`. La usan la potencia
derivada y `EnergyAccumulator`, que hoy hace el filtro en línea (`domain/energy.py:44`). Así el filtro está en un
solo sitio.

### 5.3 Energía desde la potencia derivada

La energía integra la potencia derivada. La potencia derivada es la fuente filtrada por signo, así que el
`EnergySpec` que genera `select` lleva `sources=(mode.source,)` y el `sign` del flujo. El número es idéntico al de
integrar la entidad derivada, y no hace falta un segundo camino de cálculo ni cambiar `EnergyAccumulator`.

### 5.4 Validación

`validate_profile` añade:

- Claves de modo únicas. Al menos un flujo por modo.
- `source` existe, es un sensor `power` y su componente es el principal o está declarado en `components`.
- Las claves de potencia y energía de los flujos no chocan con entidades, energías ni controles.
- Una misma clave en dos modos lleva el mismo rol y el mismo signo. Comparte `unique_id` y se mueve de
  dispositivo al cambiar de modo.
- `mode.component` puede no estar en `components`: es un dispositivo que solo crea el modo (Generador).
  `_component_problems` (`domain/validate.py:48-66`) lo acepta.

## 6. Aplicación: `select`

`select(profile, components, metering)`:

- `metering: str | None`. `None` = entry sin modo guardado: primer modo del perfil.
- Componentes elegidos = los marcados + el principal + el componente de la fuente + `mode.component`.
- `Selection` gana `powers: tuple[DerivedPowerSpec, ...]`, una por flujo del modo, en `mode.component`.
- `Selection.energies` = las del perfil (solar, batería) + una `EnergySpec` por flujo (§5.3), en
  `mode.component`.
- Perfil sin modos: `powers` vacío y nada cambia.

## 7. Adaptadores

### 7.1 Entidades y runtime

- Sensor nuevo `ModbusSolarDerivedPowerSensor` en `adapters/inbound/entities/`. Lee la fuente del coordinator de su
  tier y aplica `filter_power`. Si la fuente no tiene valor, el sensor no tiene valor.
- `build_sensors` (`adapters/inbound/entities/factory.py:93-104`) crea una por `selection.powers`.
- `enabled_keys` (`adapters/inbound/runtime.py:51-62`): una potencia derivada activa obliga a leer su fuente,
  igual que una energía.
- `_remove_unselected` (`__init__.py:28-53`): cuenta como propias las claves de todos los modos, y borra los
  dispositivos de modo que ya no estén elegidos. Al pasar a «Aislada» se borran las 4 entidades de red con su
  historial; al salir de «Aislada», las del generador.
- `device_info` (`adapters/inbound/entities/base.py:16-35`) no cambia: Generador es un componente más.

### 7.2 Flujo de alta

Paso nuevo `metering` después de `connection` y antes de `components`. Solo sale si el perfil declara modos.

- Campo `metering`: `SelectSelector` en modo desplegable, con `translation_key="metering_mode"`.
- Valor por defecto: el elegido antes en el mismo flujo; si no, el primer modo.
- Volver a `model` olvida el modo, igual que los componentes (`adapters/inbound/flow.py:327`, `:355`).

Paso `components`:

- El componente forzado por el modo sale marcado, aunque el perfil lo tenga desmarcado por defecto.
- Si se desmarca, error `metering_component_required`: «{component} hace falta para «{mode}». Márcalo o cambia la
  medición de red.»
- Generador no sale en la lista: no está en `profile.components`.

`intervals` guarda `CONF_METERING` en `entry.data`, junto a `CONF_COMPONENTS`
(`adapters/inbound/flow.py:578`).

### 7.3 Reconfigurar

Paso nuevo `reconfigure_metering` antes de `reconfigure_components`, con el mismo desplegable. Valor por defecto: el
guardado, o el primero. Descripción:

> Entre «Consumos en Grid» y «Consumos en Cargas Críticas», las potencias y energías de red cambian de dispositivo
> y conservan su historial. Al pasar a «Aislada» se borran con su historial; al salir de «Aislada» se borran las
> del generador.

`reconfigure_components` aplica la misma regla de componente forzado. `reconfigure_intervals` guarda
`CONF_METERING` (`adapters/inbound/flow.py:703`).

## 8. Datos y compatibilidad

- `CONF_METERING = "metering"` en `const.py`.
- Entry sin `metering`: primer modo, `grid_loads`. Las energías siguen en Red con la misma fuente. Solo se añaden
  las dos potencias nuevas.
- No hace falta migración de versión: el valor ausente tiene un significado fijo.
- Cambiar de modo en reconfigurar recarga la entry, como hoy al cambiar componentes.
- Las energías continúan su total tras cambiar de fuente. No vuelven a cero.

## 9. Pendiente de verificar en la VM

- Signo de 30052 con importación y con exportación.
- Signo de 30072 (supuesto de la spec del perfil, aún abierto).
- Qué leen 30070-30072 sin vatímetro externo.
- En aislada con grupo: que 30052 da la potencia del grupo.
- `entity_id` generado para las entidades nuevas en español.

## 10. Criterios de aceptación

1. El alta del STORAGE 1Play TL M muestra el paso `metering` con tres opciones y «Consumos en Grid» por defecto.
2. El alta del 1Play TL M sin batería y la del Si-RS485 no muestran el paso.
3. Con «Consumos en Grid» se crean Potencia de red y Potencia a la red en Red, y las dos energías de red siguen
   en Red.
4. Con «Consumos en Cargas Críticas» las 4 entidades están en Vatímetro interno y se calculan desde 30052.
5. Con «Aislada» existe el dispositivo Generador con su potencia y su energía, y no hay entidades de red
   derivadas.
6. Desmarcar el componente forzado da `metering_component_required`.
7. Pasar de «Consumos en Grid» a «Consumos en Cargas Críticas» en reconfigurar conserva el `unique_id` y el
   total de las energías.
8. Pasar a «Aislada» borra las 4 entidades de red; salir de «Aislada» borra el dispositivo Generador.
9. Una entry sin `metering` se comporta como «Consumos en Grid».
10. `validate_profile` acepta los perfiles del repo y rechaza los casos de §5.4.

## 11. Tests

Solo en CI (ADR 0007).

- `tests/unit/test_energy.py`: `filter_power`.
- `tests/unit/test_validate.py`: reglas de §5.4.
- `tests/unit/test_selection.py`: componentes forzados, `powers` y `energies` por modo, `metering=None`.
- `tests/unit/test_storage_profile.py`: los tres modos del perfil.
- `tests/unit/test_translations.py`: claves nuevas en `strings.json`, `es.json` y `en.json`.
- `tests/ha/test_sensor.py`: valores de las potencias derivadas con fuente positiva, negativa y sin valor.
- `tests/ha/test_energy.py`: las energías integran la fuente del modo.
- `tests/ha/test_config_flow.py`: paso `metering`, error de componente forzado, `reconfigure_metering`.
- `tests/ha/test_init.py`: borrado de entidades y del dispositivo Generador al cambiar de modo.

## 12. Piezas que cambian

| Pieza | Cambio |
|---|---|
| `domain/metering.py` | Nuevo: `FlowSpec`, `MeteringModeSpec`, `DerivedPowerSpec` |
| `domain/energy.py` | `filter_power`; `EnergyAccumulator` la usa |
| `domain/types.py` | `Component.GENERATOR`; roles nuevos |
| `domain/profile.py` | `DeviceProfile.metering_modes` |
| `domain/validate.py` | Reglas de §5.4 |
| `application/selection.py` | `select(..., metering)`, `Selection.powers` |
| `profiles/ingeteam/oneplay_storage.py` | Tres modos; las energías de red salen de `energies` |
| `adapters/inbound/entities/` | `ModbusSolarDerivedPowerSensor`; `build_sensors` |
| `adapters/inbound/runtime.py` | `enabled_keys` con las fuentes de las potencias |
| `adapters/inbound/flow.py` | Pasos `metering` y `reconfigure_metering`; regla del componente forzado |
| `__init__.py` | `select` con el modo; `_remove_unselected` con las claves y dispositivos de modo |
| `const.py` | `CONF_METERING` |
| `strings.json`, `translations/es.json`, `translations/en.json` | Pasos, selector, error, dispositivo y entidades |
| `docs/decisions/0017-metering-mode.md` | ADR nuevo: el modo de medición decide la fuente y el dispositivo |
