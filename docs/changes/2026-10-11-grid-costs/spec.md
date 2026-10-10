---
type: feature
area: energy
layers: [domain, application, adapters]
status: draft
date: 2026-10-11
refs:
  - decisions/0009-computed-energy.md
  - decisions/0017-metering-mode.md
docs:
  - features/device-setup.md
  - features/monitoring.md
  - architecture/domain.md
  - architecture/application.md
  - architecture/adapters/inbound.md
---

# Spec — Seguimiento de costes de red en el STORAGE 1Play TL M

Rutas bajo `custom_components/modbus_solar/` salvo indicación.

## 1. Objetivo y alcance

Las energías importada y exportada ya existen (`profiles/ingeteam/oneplay_storage.py:173-188`). El usuario quiere
su coste en euros, en el mismo dispositivo que esas energías, con un precio fijo o con el de una entidad de HA.

**Dentro:**

- Dos pasos nuevos en el alta y en reconfigurar: «Costes de red» y «Precios».
- Un precio por sentido (importada y exportada), cada uno fijo o dinámico.
- Dos sensores nuevos: «Coste de la energía importada» y «Coste de la energía exportada».

**Fuera:**

- Otros perfiles. El 1Play TL M sin batería no declara modos de medición.
- Monedas distintas del euro.
- Término de potencia, impuestos y peajes fijos.
- Reinicio periódico del coste (diario, mensual).
- Calcular el coste del historial anterior a activar el seguimiento.
- Configurar el panel de Energía de HA.

## 2. Hechos de partida

| Hecho | Fuente |
|---|---|
| Los flujos de red declaran potencia y energía de cada sentido | `profiles/ingeteam/oneplay_storage.py:173-188` |
| El modo «Aislada» solo tiene el flujo del generador | `profiles/ingeteam/oneplay_storage.py:448-467` |
| `select()` crea potencias y energías a partir de los flujos del modo | `application/selection.py:48-70` |
| La energía integra la potencia filtrada por el trapecio | `domain/energy.py:33-58` |
| El sensor de energía restaura su total y muestrea en cada actualización del coordinator | `adapters/inbound/entities/energy.py:27-53` |
| Las entidades de flujos que ya no se usan se borran del registro | `__init__.py:28-64` |
| Paso «Medición de red» del alta y de reconfigurar | `adapters/inbound/flow.py:460-468`, `:762-772` |

## 3. Decisiones

| Decisión | Elegida | Motivo |
|---|---|---|
| Precios | Uno por sentido, cada uno fijo o dinámico | En España, la energía exportada se compensa mucho más barata que la importada |
| Unidad del precio dinámico | Se lee `unit_of_measurement`: se aceptan €/kWh y €/MWh | PVPC publica en €/kWh y OMIE en €/MWh |
| Precio dinámico no disponible | La energía queda pendiente y se cobra con el siguiente precio válido | Ningún kWh queda sin coste; es el criterio del coste del panel Energía de HA |
| Forma del flujo | Dos pasos: modos y luego precios | Los formularios de HA no muestran campos de forma condicional |
| Cálculo | El sensor de coste integra la misma fuente y el mismo signo que su energía | No depende de que la energía esté activa ni de su `entity_id`; la lógica queda en el dominio |
| Nombres | «Coste de la energía importada» y «Coste de la energía exportada» | Elegidos por el usuario |

## 4. Datos

`entry.data` gana la clave `costs` (`CONF_COSTS = "costs"` en `const.py`):

```python
# sin seguimiento: la clave no está o vale None
"costs": {
    "import": {"mode": "fixed", "price": 0.15},          # €/kWh
    "export": {"mode": "dynamic", "entity_id": "sensor.pvpc_excedentes"},
}
```

Una entry existente no tiene `costs`: no se crean costes y todo funciona igual que hoy. No hace falta migración
ni subir `VERSION` del flow.

## 5. Dominio

### 5.1 Tipos

En `domain/metering.py`, `FlowSpec` gana dos campos opcionales:

```python
cost_key: str | None = None
cost_role: Role | None = None
```

Un flujo sin `cost_key` no tiene coste (el del generador).

En `domain/types.py`, roles nuevos: `Role.COST_GRID_IMPORT = "cost_grid_import"` y
`Role.COST_GRID_EXPORT = "cost_grid_export"`.

`DerivedCostSpec`, en `domain/metering.py`:

```python
@dataclass(frozen=True, kw_only=True)
class DerivedCostSpec:
    key: str          # también translation_key y sufijo del unique_id
    role: Role
    source: str       # la misma fuente de potencia que su energía
    sign: SignFilter
    component: Component
    direction: str    # "import" o "export": clave de su precio en entry.data["costs"]
    enabled_default: bool = True
```

### 5.2 Precio

Módulo nuevo `domain/cost.py`.

```python
def price_per_kwh(value: object, unit: str | None) -> float | None:
    """Precio en €/kWh. None si el valor no es numérico o la unidad no es de energía en euros."""
```

- Unidades aceptadas: `€/kWh`, `EUR/kWh` (factor 1) y `€/MWh`, `EUR/MWh` (factor 1/1000).
- Un valor de texto numérico (`"0.123"`, el estado de HA) se convierte a float.
- `bool`, `None`, `NaN`, infinitos y texto no numérico devuelven `None`.
- Un precio negativo es válido: hay horas con precio negativo en el mercado.

### 5.3 Acumulador

```python
class CostAccumulator:
    def __init__(self, sign: SignFilter, max_gap_s: float, total_eur: float = 0.0) -> None: ...
    @property
    def total_eur(self) -> float: ...
    def add(self, t: float, power_w: float | None, price: float | None) -> None: ...
```

- Usa un `EnergyAccumulator` interno con el mismo signo y hueco máximo. En cada `add` toma el ΔkWh de esa
  muestra: la diferencia de `total_kwh` antes y después.
- Con precio: `total_eur += (pending_kwh + delta_kwh) × price` y `pending_kwh = 0`.
- Sin precio: `pending_kwh += delta_kwh`.
- `power_w = None` corta la serie igual que en la energía (`domain/energy.py:47-50`).
- El total no se fuerza a ≥ 0: con precio negativo puede bajar.
- `pending_kwh` no se persiste. Si HA se reinicia con el precio caído, ese tramo queda sin coste. Limitación
  aceptada.

## 6. Aplicación: `select`

`Selection` gana `costs: tuple[DerivedCostSpec, ...] = ()`.

`select(profile, components, metering, costs=None)`:

- `costs` es el dict de `entry.data["costs"]` o `None`.
- Con `costs` y un modo con flujos que declaran `cost_key`, crea un `DerivedCostSpec` por flujo, con la fuente del
  modo, el signo del flujo y el componente del modo. `direction` es `"import"` para `SignFilter.POSITIVE` y
  `"export"` para `SignFilter.NEGATIVE`.
- Sin `costs` o en «Aislada», `costs = ()`.

Perfil: `GRID_FLOWS` declara `cost_key="grid_import_cost"`, `cost_role=Role.COST_GRID_IMPORT` y
`cost_key="grid_export_cost"`, `cost_role=Role.COST_GRID_EXPORT`.

Llamadores de `select` que pasan el dict guardado: `__init__.py:76` y `adapters/inbound/flow.py:545`, `:622`, `:646`, `:799`.

## 7. Adaptadores

### 7.1 Sensor de coste

`adapters/inbound/entities/cost.py`, `ModbusSolarCostSensor(ModbusSolarEntity, RestoreSensor)`:

- `device_class = monetary`, `native_unit_of_measurement = "EUR"`, `state_class = total`,
  `suggested_display_precision = 2`. HA no admite `total_increasing` con `monetary`.
- Coordinator: el del tier de su fuente, como la potencia derivada (`entities/factory.py:50-53`).
- Hueco máximo: tres intervalos del tier, como la energía (`entities/energy.py:22-23`).
- Restaura `total_eur` del último estado al arrancar.
- En cada actualización del coordinator lee la potencia de la fuente y el precio:
  - fijo: el número guardado;
  - dinámico: `hass.states.get(entity_id)` → `price_per_kwh(state.state, state.attributes.get("unit_of_measurement"))`.
- Si el precio pasa a `None`, un `warning` en el log por caída, no por muestra. Al volver, un `info`.
- `build_sensors` añade un `ModbusSolarCostSensor` por cada `selection.costs`.

### 7.2 Limpieza del registro

`_remove_unselected` (`__init__.py:28-64`) suma las `cost_key` de todos los flujos a las claves de la
integración. Así, desmarcar el seguimiento borra los sensores de coste, igual que hoy con un modo que se deja.

### 7.3 Flujo de alta

Tras `metering`, si el modo elegido tiene algún flujo con `cost_key`, se muestra el paso `costs`. Si no, se sigue
como hoy.

Paso `costs`:

| Campo | Selector | Por defecto |
|---|---|---|
| `enabled` | booleano «Seguimiento de costes» | `False` |
| `import_mode` | desplegable `fixed` / `dynamic` | `fixed` |
| `export_mode` | desplegable `fixed` / `dynamic` | `fixed` |

Con `enabled = False` se guarda `costs = None` y se salta `cost_prices`.

Paso `cost_prices`, con un campo por sentido según su modo:

| Modo | Campo | Selector |
|---|---|---|
| `fixed` | `import_price` / `export_price` | `NumberSelector`, 0 a 10, paso libre (`"any"`: HA exige paso ≥ 0,001 y las tarifas llevan 4 decimales), unidad €/kWh, modo caja |
| `dynamic` | `import_entity` / `export_entity` | `EntitySelector`, dominio `sensor` |

Al enviar, cada entidad dinámica se valida: debe existir y su `unit_of_measurement` debe ser una de las de §5.2.
Si no, error `price_unit_invalid` en ese campo y se queda en el paso. El estado actual de la entidad no se valida:
puede estar `unavailable` en ese momento.

### 7.4 Reconfigurar

Pasos `reconfigure_costs` y `reconfigure_cost_prices`, tras `reconfigure_metering`, con la misma lógica. Por
defecto, los valores guardados. Si se cambia a un modo sin flujos con coste («Aislada»), se guarda `costs = None`.

### 7.5 Traducciones

`strings.json`, `translations/en.json` y `translations/es.json`:

- Pasos `costs`, `cost_prices`, `reconfigure_costs` y `reconfigure_cost_prices`, con títulos y etiquetas.
- `selector.cost_mode.options`: `fixed` «Precio fijo», `dynamic` «Precio dinámico (entidad)».
- Error `price_unit_invalid`: «La entidad debe tener unidad €/kWh o €/MWh».
- Entidades `grid_import_cost` «Coste de la energía importada» y `grid_export_cost` «Coste de la energía
  exportada». En inglés, «Grid import cost» y «Grid export cost».

## 8. Criterios de aceptación

1. Alta con «Consumos en Grid» y sin marcar la casilla: no hay sensores de coste y la entry no guarda `costs`.
2. Alta con la casilla marcada, importada fija a 0,15 y exportada dinámica: el dispositivo Red tiene los dos
   sensores de coste en EUR.
3. Con «Consumos en Cargas Críticas», los costes van al dispositivo Vatímetro interno, como sus energías.
4. Con «Aislada» no aparecen los pasos de costes.
5. Una entidad dinámica sin unidad válida da `price_unit_invalid`.
6. Una entidad en €/MWh con 120 da 0,12 €/kWh.
7. Con el precio caído, el coste no sube. Al volver, suma la energía pendiente con el nuevo precio.
8. El coste se restaura al reiniciar HA.
9. Reconfigurar y desmarcar la casilla borra los dos sensores del registro.
10. Una entry de 0.2.0 arranca sin cambios.

## 9. Tests

| Test | Fichero |
|---|---|
| `price_per_kwh`: unidades, texto numérico, no numérico, NaN, negativo | `tests/unit/test_cost.py` |
| `CostAccumulator`: con precio, sin precio y pendiente, huecos, total restaurado | `tests/unit/test_cost.py` |
| `select` con y sin `costs`, y en «Aislada» | `tests/unit/test_selection.py` |
| Perfil STORAGE: costes de los flujos de red | `tests/unit/test_storage_profile.py` |
| Flujo: pasos según modo, casilla, error de unidad, reconfigurar | `tests/ha/` (flow) |
| Sensor: fijo, dinámico, caída del precio y restauración | `tests/ha/` (sensor de coste) |
| Limpieza del registro al desmarcar | `tests/ha/test_init.py` |

## 10. Piezas que cambian

| Pieza | Cambio |
|---|---|
| `domain/cost.py` | Nuevo: `price_per_kwh`, `CostAccumulator` |
| `domain/metering.py` | `FlowSpec.cost_key/cost_role`, `DerivedCostSpec` |
| `domain/types.py` | Roles `COST_GRID_IMPORT`, `COST_GRID_EXPORT` |
| `application/selection.py` | `Selection.costs`, parámetro `costs` de `select` |
| `profiles/ingeteam/oneplay_storage.py` | `cost_key` y `cost_role` en `GRID_FLOWS` |
| `adapters/inbound/entities/cost.py` | Nuevo: `ModbusSolarCostSensor` |
| `adapters/inbound/entities/factory.py` | Crea los sensores de coste |
| `adapters/inbound/flow.py` | Pasos de costes en el alta y en reconfigurar |
| `__init__.py` | Pasa `costs` a `select`; limpieza del registro |
| `const.py` | `CONF_COSTS` |
| `strings.json`, `translations/*.json` | Pasos, selector, error y entidades |
