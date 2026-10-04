---
type: feature
area: control
layers: [domain, ports, application, adapters, profiles]
status: draft
date: 2026-10-04
---

# Spec 3 — Escritura de parámetros y control del vertido

> Es la «Spec 2: escritura» que dejaron anotada `docs/changes/2026-10-04-storage-profile/spec.md:28-29` y
> `docs/changes/2026-10-04-skeleton/spec.md:30-31`. El número 2 ya lo usa el flujo de alta
> (`docs/changes/2026-10-04-setup-flow/spec.md`), por eso esta es la 3.

## 1. Objetivo y alcance

Hasta ahora la integración solo lee: `PLATFORMS = [HaPlatform.SENSOR]`
(`custom_components/modbus_solar/__init__.py:21`) y el puerto `DeviceGateway` solo tiene `read`
(`ports/device.py:9-12`). Esta spec añade la primera ruta de escritura Modbus, genérica y declarada en
el perfil, y la usa para el control del vertido del INGECON SUN STORAGE 1Play TL M.

**Dentro:**
- Ruta de escritura de comandos Ingeteam (FC16 sobre la zona de comandos 1000-1002), a través de un
  puerto nuevo (§4).
- Un tipo de control nuevo, `GatedLimitSpec`: un límite en W con un interruptor que lo activa (§3, §4).
- Plataformas HA `number` y `switch` (§5).
- En el perfil `ingeteam.oneplay_storage`: potencia máxima de vertido y switch de vertido (§3).

**Fuera:**
- **Potencia contratada** («Hired Grid Power» / «Power Contracted»). Ningún documento aporta comando ni
  registro Modbus para escribirla: ni `AAA0030IMB03_N.pdf` (holding 1000-1021 y CMD 0-37, págs. 4-8),
  ni `ABH2010IMB08` (input 30001-30081), y en `ABH2014IQM01` solo aparece como ajuste de pantalla
  (pág. 54). Se investigará con una herramienta de sondeo de solo lectura, en una sesión aparte
  (worktree `register-probe`).
- Otros parámetros de batería (CMD 24, resto de datos del CMD 26: corrientes, SOC, carga desde red…).
  El diseño general (§4) los admite añadiendo tipos de control; no se implementan aquí.
- Lectura del valor real del ajuste de vertido. No hay registro que lo dé (§2.3).
- Perfil `ingeteam.oneplay` (el mapa viejo sin storage): no lleva controles.

**Criterios de éxito:**
1. Un STORAGE 1Play TL M con el perfil `ingeteam.oneplay_storage` muestra un switch y un number de
   vertido.
2. Con el switch en OFF, el inversor recibe 0 W como «Grid power». Con el switch en ON, recibe el valor
   del number.
3. Cambiar el number con el switch en ON escribe el valor nuevo. Con el switch en OFF solo lo guarda.
4. Tras reiniciar HA, switch y number conservan su último valor y **no escriben nada** al equipo.
5. Una escritura fallida deja la entidad como estaba y lanza `HomeAssistantError`.
6. Un perfil sin controles (`ingeteam.oneplay`) no crea ninguna entidad `number` ni `switch`.

## 2. Contexto técnico verificado

### 2.1 Protocolo de comandos (`AAA0030IMB03_N`, rev. N, 20/05/2024)

- Solo FC03, FC06 y FC16 (pág. 3). Los comandos van en holding desde la dirección **1000 (0x03E8)**
  (pág. 3).
- Para ejecutar: escribir código de comando y datos; cualquier escritura en 1000 se interpreta como
  ejecución (pág. 3).

| Dirección | Registro | Descripción | Tipo |
|---|---|---|---|
| 1000 | 41001 | Command Code | R/W |
| 1001 | 41002 | Command Data 1 | R/W |
| 1002 | 41003 | Command Data 2 | R/W |

(pág. 4)

- **CMD 26 «Battery Control Values»** (págs. 6-7, 19): dato 1 elige el parámetro; dato 2 es su valor.
  - Trama de ejemplo para «Grid power» 3000 W: `01 10 03 E8 00 03 06 00 1A 00 0A 0B B8 + CRC`
    (pág. 19). Código `0x1A` = 26, dato 1 `0x0A`, dato 2 `0x0BB8`.
  - Respuesta: `01 10 03 E8 00 03 + CRC` (pág. 19).
  - Dato `0x0A` = «Grid power»: «Maximum surplus PV power injected into the Grid» (pág. 20).
  - Rango de «Grid power»: `[6000W, -6000W]` (pág. 7). El PDF no explica qué significan los valores
    negativos: no se exponen.
- Nota 3 (pág. 8): con FC16, código y datos van en **la misma escritura**. Con FC06 habría que escribir
  primero el dato.
- El CMD 26 está descrito para batería «Lead-Acid» o «Ingeteam RS485 Protocol» (pág. 19). El PDF no
  dice si el valor sobrevive a un reinicio del inversor.
- En el manual, el mismo parámetro es «Configuration > Advanced Settings > Operation Mode > Maximum
  surplus PV power injected into the Grid», en vatios, y «si no quieres inyectar excedente a la red,
  escribe 0 W» (`ABH2014IQM01` apdo. 19.7.7, pág. 54).
- La potencia nominal por variante (3, 4,5 y 6 kW) que da `ABH2014IQM01` en su tabla de características
  es la de la entrada AC auxiliar red/grupo. El manual no da en esa tabla la potencia nominal de
  inyección a red. El máximo de 6000 W del number sale del rango del PDF (pág. 7), no de la ficha del
  equipo.

### 2.2 Librería de conexión

`modbus_connection` 4.10.0 (la que fija el manifest de `modbus` de HA 2026.9; ADR 0003):

- `ModbusUnit.write_registers(address: int, values: list[int]) -> None` es FC16
  (`modbus_connection/_protocol.py:18`).
- El mock de pruebas implementa `write_registers`: guarda los valores en `holding`, dispara
  `WriteEvent("holding", address, values, 0x10)` a los callbacks de `on_write` y admite `fail_write`
  (`modbus_connection/mock.py:140`, `:152`, `:271-277`). No guarda una lista de escrituras: los tests
  la montan con `unit.on_write(events.append)`.
- El espaciado entre peticiones lo aplica `Pacer.paced` con un `asyncio.Lock` por conexión
  (`modbus_connection/_pacing.py`). Una escritura espera detrás de las lecturas en curso, así que no se
  mezclan tramas. Un ciclo de lectura largo retrasa la escritura unos segundos.

### 2.3 Lectura del estado: no existe

- Los holding 1000-1021 legibles (`AAA0030IMB03_N` pág. 4) no incluyen «Grid power». Sí incluyen
  «Charge Power from Grid/Genset» (1020) y «SOC OFF Diesel Generator» (1021), que son los datos 9 y 16
  del mismo comando.
- Los input registers de `ABH2010IMB08` tampoco lo tienen. Solo existe una señal indirecta: el registro
  30042 «Active Power Reduction Reason», valor 16 = «PV Surplus Injected to the Grid» (Nota 7,
  pág. 7). Indica que el inversor está limitando ahora por este motivo, no cuál es el ajuste. Ya es una
  entidad extra del perfil (`power_reduction_reason`, `storage-profile/spec.md` §3.3).
- Consecuencia: si alguien cambia el vertido desde los ajustes del inversor, HA no puede enterarse con
  la documentación disponible. Decisión de producto: **estado optimista y restaurado** (§5.3).

## 3. Modelo del perfil

### 3.1 `WriteSpec` y `GatedLimitSpec` (`domain/control.py`, nuevo)

```python
@dataclass(frozen=True, kw_only=True)
class WriteSpec:
    address: int              # primera dirección de la escritura (1000)
    prefix: tuple[int, ...]   # palabras fijas antes del valor: (26, 0x0A)
    dtype: DataType = DataType.S16
    scale: float = 1.0        # palabra = round(valor / scale)

@dataclass(frozen=True, kw_only=True)
class GatedLimitSpec:
    key: str                  # clave del number y sufijo de su unique_id: "export_limit"
    switch_key: str           # clave del switch: "export_enabled"
    role: Role                # Role.EXPORT_LIMIT
    switch_role: Role         # Role.EXPORT_ENABLED
    write: WriteSpec
    min_value: float
    max_value: float
    step: float
    unit: str
    default: float            # límite inicial si no hay valor restaurado
    off_value: float = 0.0    # valor que se escribe al apagar el switch
    device_class: str | None = None
    enabled_default: bool = True   # number y switch; lo lee ModbusSolarEntity como en EntitySpec
```

- `DeviceProfile` gana `controls: tuple[GatedLimitSpec, ...] = ()`, junto a `energies`
  (`domain/profile.py:48`).
- `WriteSpec` solo admite `dtype` de 16 bits en esta spec. `validate_profile` lo comprueba.
- `Role` (`domain/types.py:143`) gana `EXPORT_LIMIT = "export_limit"` y `EXPORT_ENABLED =
  "export_enabled"`. `Platform` (`domain/types.py:171-172`) no cambia: la usa `EntitySpec.platform` y los
  controles no son `EntitySpec`; number y switch salen de `controls`, no de un valor de `Platform`.

### 3.2 Codificación (`domain/encode.py`, nuevo)

`encode(spec: WriteSpec, value: float) -> tuple[int, ...]`, inverso de `decode`
(`domain/decode.py:10-34`):

- `raw = round(value / scale)`.
- Comprueba que `raw` cabe en el tipo (S16: -32768…32767; U16: 0…65535); si no, lanza `EncodeError`. Un
  valor no finito (`nan`, `inf`) también lanza `EncodeError`.
- Un valor negativo pasa a complemento a dos de 16 bits (`raw + 0x10000`).
- Devuelve `spec.prefix + (palabra,)`.

### 3.3 Estado del límite (`domain/control.py`)

```python
@dataclass
class GatedState:
    limit: float
    enabled: bool = True
    def effective(self, spec: GatedLimitSpec) -> float:
        return self.limit if self.enabled else spec.off_value
```

Estado en memoria, uno por control, compartido por el number y el switch de un mismo `GatedLimitSpec`.

### 3.4 Validación (`domain/validate.py`)

Se añaden comprobaciones:
- clave del number o del switch duplicada, o repetida con una entidad o energía;
- `min_value > max_value`, `step <= 0`, `default` fuera de rango, `off_value` fuera de
  `[min_value, max_value]`;
- `WriteSpec.dtype` de más de 16 bits, `scale == 0`;
- `prefix` + valor no caben en una petición: más de `max_block_registers` palabras;
- el valor de `off_value` y los extremos de rango no se codifican en el tipo (`EncodeError`).

### 3.5 Perfil STORAGE (`profiles/ingeteam/oneplay_storage.py`)

```python
controls=(
    GatedLimitSpec(
        key="export_limit",
        switch_key="export_enabled",
        role=Role.EXPORT_LIMIT,
        switch_role=Role.EXPORT_ENABLED,
        # CMD 26, dato 0x0A «Grid power» (AAA0030IMB03_N págs. 7, 19-20)
        write=WriteSpec(address=1000, prefix=(26, 0x0A)),
        min_value=0, max_value=6000, step=1, unit="W", default=6000,
        device_class="power",
    ),
),
```

- Un helper `_command(code, data1)` documenta los números del PDF (`0x1A`, `0x0A`) en un sitio,
  igual que `_input` documenta los registros (`profiles/ingeteam/oneplay_storage.py:38-40`).
- `default=6000` es el máximo del rango del PDF. No se escribe nada hasta que el usuario actúa (§5.3).
- `ingeteam.oneplay` queda sin `controls`.

## 4. Puerto, casos de uso y gateway

### 4.1 Puerto `DeviceWriter` (`ports/device.py`)

```python
class DeviceWriter(Protocol):
    async def write(self, spec: WriteSpec, value: float) -> None:
        """Escribe el valor ya validado. Lanza DeviceUnavailable o DeviceProtocolError."""
        ...
```

Separado de `DeviceGateway` (segregación de interfaces: el poller y el config flow solo leen). Los
errores son los de dominio (`domain/errors.py`). `EncodeError` es una excepción de dominio nueva,
independiente de `DecodeError` (leer y escribir no comparten manejo).

### 4.2 Casos de uso (`application/control.py`, nuevo)

Reciben el `DeviceWriter`, el `GatedLimitSpec` y el `GatedState`. No importan HA ni `modbus_connection`.

- `set_limit(writer, spec, state, value)`:
  1. valida `min_value ≤ value ≤ max_value`;
  2. si `state.enabled`, escribe `value`;
  3. solo si no hubo error, `state.limit = value`.
- `set_enabled(writer, spec, state, enabled)`:
  1. escribe `state.limit` si `enabled`, o `spec.off_value` si no;
  2. solo si no hubo error, `state.enabled = enabled`.
- El estado cambia **después** de una escritura correcta. Un error deja el estado intacto.

### 4.3 Adaptador de salida (`adapters/outbound/modbus_gateway.py`)

`ModbusGateway` implementa también `DeviceWriter`:

- `write(spec, value)`: `words = encode(spec, value)`; una petición `unit.write_registers(spec.address,
  list(words))` (FC16, una sola trama, Nota 3 del PDF).
- Traduce las excepciones igual que `read` (`modbus_gateway.py:36-39`): `ModbusConnectionError` y
  `ModbusTimeoutError` a `DeviceUnavailable`; `ModbusExceptionError` y `ModbusProtocolError` a
  `DeviceProtocolError`.
- Reutiliza el espaciado ya configurado (`modbus_gateway.py:25`): no añade un segundo mecanismo.

### 4.4 Cómo se añade otro control

Un parámetro nuevo (p. ej. SOC mínimo, CMD 26 dato 6) es: un dataclass de control nuevo (o un
`GatedLimitSpec` más), su entrada en `DeviceProfile` y una clase de entidad. Puerto, gateway,
`WriteSpec` y `encode` no cambian. Un control sin interruptor es el siguiente tipo previsible
(`NumberControlSpec`); no se crea ahora (YAGNI).

## 5. Adaptadores de entrada y entidades

### 5.1 Runtime

`DeviceRuntime` (`adapters/inbound/runtime.py:18-24`) gana:

- `writer: DeviceWriter`;
- `control_states: dict[str, GatedState]`, creado en `build_runtime` con `GatedState(limit=spec.default)`
  por cada `profile.controls`.

`async_setup_entry` pasa `gateway` también como `writer` (`__init__.py:29-31`).
`PLATFORMS` pasa a `[SENSOR, NUMBER, SWITCH]` (`__init__.py:21`).

### 5.2 Plataformas

- `number.py` y `switch.py` en la raíz del componente, como `sensor.py`.
- Fábricas `build_numbers` y `build_switches` junto a `build_sensors`
  (`adapters/inbound/entities/factory.py:45-56`).
- `ModbusSolarNumber` (`RestoreNumber`) y `ModbusSolarSwitch` (`RestoreEntity`) heredan de
  `ModbusSolarEntity` (`adapters/inbound/entities/base.py:70`). `ModbusSolarEntity` acepta ya
  `EntitySpec | EnergySpec`; se amplía a `GatedLimitSpec` con el `key` correspondiente.
- **Disponibilidad:** igual que los sensores, nacen `unavailable` hasta la primera lectura correcta
  (`base.py:90-93`). Se asocian al coordinador del tier de `profile.probe_key`: si el equipo no
  responde a las lecturas, no se ofrece escribir.
- Number: `native_min_value`, `native_max_value`, `native_step`, `native_unit_of_measurement`,
  modo `box`. Switch sin `device_class` y con `assumed_state = True`: el equipo no permite leer el
  ajuste, así que HA muestra lo último que escribió y no lo que hay (§2.3).
- `unique_id`: `{entry_id}_{key}` (`runtime.py:30-32`), con las claves `export_limit` y
  `export_enabled`.

### 5.3 Comportamiento

- **Number:** `async_set_native_value(v)` llama a `set_limit`. Con el switch OFF solo guarda el valor.
- **Switch:** `async_turn_on` / `async_turn_off` llaman a `set_enabled`.
- **Errores:** `DeviceUnavailable`, `DeviceProtocolError` y `EncodeError` se traducen a
  `HomeAssistantError` con un mensaje traducible. El estado no cambia.
- **Estado optimista y restaurado:**
  - El number restaura su último valor con `async_get_last_number_data()`; el switch, su último estado.
  - La restauración **no escribe** al equipo. Tras un reinicio de HA el inversor conserva lo que tenía.
  - Primer arranque (nada que restaurar): number = `default`, switch ON, sin escritura.
- El switch y el number son independientes en pantalla: apagar el switch no cambia el valor del number.
- HA no sabe si el ajuste se cambió desde el inversor. Se documenta (§7). El sensor
  `power_reduction_reason` (valor 16) indica si el límite actúa en este momento.

### 5.4 Traducciones

`strings.json`, `translations/en.json` y `translations/es.json` ganan `entity.number.export_limit`,
`entity.switch.export_enabled` y un mensaje de error de escritura. `tests/unit/test_translations.py` ya
comprueba que cada clave de entidad tiene traducción; se amplía a las plataformas nuevas.

## 6. Tests

Solo en CI (ADR 0007, memoria `tests-ci-only`).

- **Unitarios:**
  - `encode`: 0, 6000, negativo (complemento a dos), valor fuera de rango (`EncodeError`), escala.
  - `GatedState.effective`.
  - Casos de uso con un `FakeWriter`: escribe `limit` o `off_value` según el switch; estado intacto si
    la escritura falla; valor fuera de rango rechazado.
  - `validate_profile` con controles: cada comprobación nueva de §3.4.
  - Perfil STORAGE: `controls` válido, `write.address == 1000`, `write.prefix == (26, 10)`.
  - `ModbusGateway.write` contra `MockModbusUnit`: un `WriteEvent` FC16 `[26, 10, W]` en la dirección
    1000; los errores se traducen a `DeviceUnavailable` / `DeviceProtocolError`.
- **HA:**
  - STORAGE crea number y switch; `ingeteam.oneplay` no crea ninguno.
  - Switch OFF escribe `[26, 10, 0]`; ON escribe `[26, 10, limite]`.
  - Number con switch ON escribe; con switch OFF no escribe.
  - Una escritura fallida lanza `HomeAssistantError` y el estado no cambia.
  - Restauración tras recargar la entry: valores recuperados y ningún `WriteEvent`.
  - Disponibilidad: `unavailable` antes de la primera lectura y si el equipo cae.
- **Sin test propio:** que una escritura no solape tramas con una lectura. Lo garantiza el `Pacer` de
  `modbus_connection` (§2.2) y el mock no lo reproduce. Se comprueba en la VM.

## 7. Documentación

- `docs/features/control.md` (nuevo): switch y number de vertido, estado optimista y su límite, qué
  significa 0 W, sensor `power_reduction_reason`.
- `docs/architecture/`: `domain.md` (`WriteSpec`, `GatedLimitSpec`, `GatedState`, `encode`), `ports.md`
  (`DeviceWriter`), `adapters/outbound.md` (`write`), `adapters/inbound.md` (plataformas nuevas),
  `application.md` (casos de uso).
- ADR 0011 «Controles declarados en el perfil y escritura por puerto separado» y ADR 0012 «Estado
  optimista y restaurado cuando el equipo no permite leer el ajuste».
- `docs/wiki/brands/ingeteam/README.md`: anotar que el CMD 26 dato `0x0A` es el vertido y que la
  potencia contratada no tiene comando documentado.

## 8. Riesgos y pendientes

- **Estado no verificable.** Cambios hechos desde el inversor no se reflejan. Si el sondeo de
  `register-probe` encuentra un registro, se añade lectura sin cambiar el modelo de §3.
- **Persistencia.** El PDF no dice si el CMD 26 sobrevive a un reinicio del inversor. Si no persiste, el
  vertido volvería al ajuste local sin que HA lo sepa. Se comprueba en la VM. Si ocurre, se plantea una
  reescritura periódica en otra spec.
- **Batería configurada.** El CMD 26 se describe para batería «Lead-Acid» o «Ingeteam RS485 Protocol»
  (pág. 19). Con otra configuración el comando podría no aplicarse. Se verifica en la VM.
- **Ejecución del comando.** Los holding 1000-1002 son legibles (pág. 4); una lectura posterior podría
  confirmar que el equipo aceptó el comando. No forma parte de esta spec.
- **Signo del rango.** Los valores negativos de «Grid power» no están explicados (pág. 7); el number
  no los permite.
- **Máximo por variante.** El máximo del number es 6000 W para todas las variantes. No se ha
  verificado la potencia nominal de inyección de cada variante; ajustar el máximo por variante queda
  fuera de esta spec.
- **Escrituras compartidas.** Con otro cliente Modbus conectado, Ingeteam no garantiza las respuestas
  (`ABH2014IQM01`, pág. 50), también para las escrituras.
- **Latencia.** Una escritura espera detrás de las lecturas en curso (§2.2). Con el tier `fast` de
  3 peticiones y 1 s de espaciado, serán 1-3 s.
