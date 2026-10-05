# STORAGE 1Play TL M: input registers (ABH2010IMB08)

Extraído de `ABH2010IMB08.pdf` (revisión _I, 23/04/2025). Ante discrepancia, manda el PDF.
Escalas y orden de palabras de los registros de 32 bits sin verificar en equipo.

- Lectura con la función 0x04 (Read Input Registers), referencias 3xxxx (PDF pág. 9).
- El registro 30001 es la dirección 0 del protocolo: dirección = registro − 30001 (PDF pág. 9).
- `Página` es la página del PDF donde está la fila. Se omite la columna «Since FW Ver.».
- 30008 y 30012 no tienen fila propia en el PDF: son la segunda palabra de 30007 y 30011 (UINT32).
- El mapa no trae ningún contador de energía.
- `Componente`: dispositivo de HA donde va o iría la entidad del registro (enum `Component`, spec
  setup-flow-v2 §5.1). `—`: reservado.
- `En HA`: si el registro sale como entidad en Home Assistant. `sí`: hoy; `prevista`: en una spec en curso
  (30043, reason-labels); `no`: no se lee.
- `entity_id`: el que HA generará al crear la entidad en una entry nueva con Device ID 0:
  `<plataforma>.<dispositivo>_<device_id>_<nombre>`, sin tildes ni signos. Dispositivo y nombre de entidad en
  español, patrón A de setup-flow-v2 §5.4 (la entidad no repite su dispositivo). Con otro Device ID cambia el
  número: `sensor.bateria_1_tension` (setup-flow-v2 §5.6). Una entry sin Device ID, creada antes de v2, no lleva
  número, y las entries ya creadas conservan su `entity_id`. Pendiente de verificar en la VM que HA lo genera en
  español. `—`: no se expone.
- `Tier`: frecuencia de lectura en la integración (instant 5 s, fast 10 s, normal 60 s, slow 1 h). Las entidades
  principales llevan el de hoy, salvo las de red, en `instant` (setup-flow-v2 §5.8); el resto, la propuesta de
  «Tier y activación de las entidades de diagnóstico». `—`: no se lee.
- El manual `ABH2014IQM01.pdf` (apdo. 19.6.1, pág. 50) recomienda un único cliente en el puerto 502,
  al menos 1 s entre peticiones y no más de 10 registros por petición.

| Registro | Nombre (PDF) | Nombre corto (ES) | Tipo | Unidad / nota | Página | Componente | En HA | Tier | entity_id |
|---|---|---|---|---|---|---|---|---|---|
| `30001` | Current Date. Year | Fecha: Año | UINT16 |  | 3 | Inversor | no | — | — |
| `30002` | Current Date. Month | Fecha: Mes | UINT16 |  | 3 | Inversor | no | — | — |
| `30003` | Current Date. Day | Fecha: Día | UINT16 |  | 3 | Inversor | no | — | — |
| `30004` | Current Date. Hour | Fecha: Hora | UINT16 |  | 3 | Inversor | no | — | — |
| `30005` | Current Date. Minute | Fecha: Minuto | UINT16 |  | 3 | Inversor | no | — | — |
| `30006` | Current Date. Second | Fecha: Segundo | UINT16 |  | 3 | Inversor | no | — | — |
| `30007` | Inverter. Total operation time | Horas de operación | UINT32 | [h] | 3 | Inversor | sí | slow | `sensor.inversor_0_tiempo_de_funcionamiento` |
| `30008` | (segunda palabra de 30007) | (segunda palabra) |  |  | 3 | Inversor | sí | slow | (la de 30007) |
| `30009` | Reserved for Ingeteam | Reservado |  |  | 3 | — | no | — | — |
| `30010` | Stop Event | Evento de parada | UINT16 | [Note 1] | 3 | Inversor | no | — | — |
| `30011` | Alarms | Alarmas activas | UINT32 | [Note 1] | 3 | Inversor | no | — | — |
| `30012` | (segunda palabra de 30011) | (segunda palabra) |  |  | 3 | Inversor | no | — | — |
| `30013` | Code 1 | Código de alarma 1 | UINT16 | [Note 1] | 3 | Inversor | no | — | — |
| `30014` | Code 2 | Código de alarma 2 | UINT16 | [Note 1] | 3 | Inversor | no | — | — |
| `30015` | Code 3 | Código de alarma 3 | UINT16 | [Note 1] | 3 | Inversor | no | — | — |
| `30016` | Inverter Status | Estado inversor | UINT16 | [Note 2] | 3 | Inversor | sí | fast | `sensor.inversor_0_estado` |
| `30017` | Waiting Time to Connect to Grid | Espera conexión red | UINT16 | [sec] | 3 | Inversor | no | — | — |
| `30018` | Battery. Voltage | Tensión batería | UINT16 | [V x 10] | 3 | Batería | sí | normal | `sensor.bateria_0_tension` |
| `30019` | Battery. Current | Corriente batería | INT16 | [A x 100] | 3 | Batería | sí | normal | `sensor.bateria_0_corriente` |
| `30020` | Battery. Power | Potencia batería | INT16 | [W] | 3 | Batería | sí | fast | `sensor.bateria_0_potencia` |
| `30021` | Battery. SOC | SOC batería | UINT16 | [%] | 3 | Batería | sí | fast | `sensor.bateria_0_estado_de_carga` |
| `30022` | Battery. SOH | SOH batería | UINT16 | [%] | 3 | Batería | sí | slow | `sensor.bateria_0_estado_de_salud` |
| `30023` | Battery. Charging Voltage | Límite tensión carga | UINT16 | [V x 10] | 3 | Batería | no | — | — |
| `30024` | Battery. Discharging Voltage | Límite tensión descarga | UINT16 | [V x 10] | 3 | Batería | no | — | — |
| `30025` | Battery. Max. Charging Current | Corriente máx. carga | UINT16 | [A x 100] | 3 | Batería | no | — | — |
| `30026` | Battery. Max. Discharging Current | Corriente máx. descarga | UINT16 | [A x 100] | 3 | Batería | no | — | — |
| `30027` | Battery. Status | Estado batería | UINT16 | [Note 3] | 3 | Batería | sí | normal | `sensor.bateria_0_estado` |
| `30028` | Battery. Temperature | Temperatura batería | INT16 | [ºC x 10] | 3 | Batería | sí | slow | `sensor.bateria_0_temperatura` |
| `30029` | Battery. BMS Alarms | Alarmas BMS | UINT16 | [Note 4] | 3 | Batería | sí | fast | `binary_sensor.bateria_0_alarma_corriente_de_carga_alta`<br>`binary_sensor.bateria_0_alarma_tension_alta`<br>`binary_sensor.bateria_0_alarma_tension_baja`<br>`binary_sensor.bateria_0_alarma_temperatura_alta`<br>`binary_sensor.bateria_0_alarma_temperatura_baja`<br>`binary_sensor.bateria_0_alarma_fallo_interno_del_bms`<br>`binary_sensor.bateria_0_alarma_desequilibrio_de_celdas`<br>`binary_sensor.bateria_0_alarma_corriente_de_descarga_alta`<br>`binary_sensor.bateria_0_alarma_error_del_sistema_bms` |
| `30030` | Battery. Discharge Limitation Reason | Motivo límite descarga | UINT16 | [Note 9] | 3 | Batería | sí | normal | `sensor.bateria_0_motivo_de_limitacion_de_descarga` |
| `30031` | Battery. Voltage Internal Sensor | Tensión interna batería | UINT16 | [V x 10] | 3 | Batería | no | — | — |
| `30032` | PV1. Voltage | Tensión FV1 | UINT16 | [V] | 3 | Campo solar | sí | normal | `sensor.campo_solar_0_tension_fv1` |
| `30033` | PV1. Current | Corriente FV1 | UINT16 | [A x100] | 3 | Campo solar | sí | normal | `sensor.campo_solar_0_corriente_fv1` |
| `30034` | PV1. Power | Potencia FV1 | UINT16 | [W] | 4 | Campo solar | sí | fast | `sensor.campo_solar_0_potencia_fv1` |
| `30035` | PV2. Voltage | Tensión FV2 | UINT16 | [V] | 4 | Campo solar | sí | normal | `sensor.campo_solar_0_tension_fv2` |
| `30036` | PV2. Current | Corriente FV2 | UINT16 | [A x100] | 4 | Campo solar | sí | normal | `sensor.campo_solar_0_corriente_fv2` |
| `30037` | PV2. Power | Potencia FV2 | UINT16 | [W] | 4 | Campo solar | sí | fast | `sensor.campo_solar_0_potencia_fv2` |
| `30038` | Inverter. Active Power | Potencia activa inversor | INT16 | [W] | 4 | Inversor | sí | fast | `sensor.inversor_0_potencia_activa` |
| `30039` | Inverter. Reactive Power | Potencia reactiva inversor | INT16 | [Var, Note 5] | 4 | Inversor | sí | fast | `sensor.inversor_0_potencia_reactiva` |
| `30040` | Inverter. Cosφ | Factor potencia inversor | INT16 | [x1000, Note 6] | 4 | Inversor | sí | fast | `sensor.inversor_0_factor_de_potencia` |
| `30041` | Active Power Reduction Ratio | Ratio reducción potencia | UINT16 | [% x10] | 4 | Inversor | sí | normal | `sensor.inversor_0_ratio_de_reduccion_de_potencia` |
| `30042` | Active Power Reduction Reason | Motivo reducción potencia | UINT16 | [Note 7] | 4 | Inversor | sí | normal | `sensor.inversor_0_motivo_de_reduccion_de_potencia` |
| `30043` | Reactive Power Set-Point Type | Modo control reactiva | UINT16 | [Note 8] | 4 | Inversor | prevista | slow | `sensor.inversor_0_tipo_de_consigna_de_reactiva` |
| `30044` | Critical Loads. Voltage | Tensión backup | UINT16 | [V] | 4 | Cargas críticas | sí | fast | `sensor.cargas_criticas_0_tension` |
| `30045` | Critical Loads. Current | Corriente backup | UINT16 | [A x100] | 4 | Cargas críticas | sí | fast | `sensor.cargas_criticas_0_corriente` |
| `30046` | Critical Loads. Frequency | Frecuencia backup | UINT16 | [Hz x100] | 4 | Cargas críticas | sí | fast | `sensor.cargas_criticas_0_frecuencia` |
| `30047` | Critical Loads. Active Power | Potencia backup | INT16 | [W] | 4 | Cargas críticas | sí | fast | `sensor.cargas_criticas_0_potencia` |
| `30048` | Critical Loads. Reactive Power | Potencia reactiva backup | INT16 | [Var, Note 5] | 4 | Cargas críticas | no | — | — |
| `30049` | Internal Wattmeter Grid. Voltage | Tensión red interna | UINT16 | [V] | 4 | Vatímetro interno | sí | fast | `sensor.vatimetro_interno_0_tension` |
| `30050` | Internal Wattmeter Grid. Current | Corriente red interna | UINT16 | [A x100] | 4 | Vatímetro interno | sí | fast | `sensor.vatimetro_interno_0_corriente` |
| `30051` | Internal Wattmeter Grid. Frequency | Frecuencia red interna | UINT16 | [Hz x100] | 4 | Vatímetro interno | sí | fast | `sensor.vatimetro_interno_0_frecuencia` |
| `30052` | Internal Wattmeter Grid. Active Power | Potencia red interna | INT16 | [W] | 4 | Vatímetro interno | sí | fast | `sensor.vatimetro_interno_0_potencia` |
| `30053` | Internal Wattmeter Grid. Reactive Power | Reactiva red interna | INT16 | [Var, Note 5] | 4 | Vatímetro interno | no | — | — |
| `30054` | Internal Wattmeter Grid. Cosφ | Factor potencia red interna | INT16 | [x1000, Note 6] | 4 | Vatímetro interno | no | — | — |
| `30055` | DC Bus Voltage | Tensión bus DC | UINT16 | [V] | 4 | Inversor | sí | fast | `sensor.inversor_0_tension_del_bus_dc` |
| `30056` | Reserved | Reservado |  |  | 4 | — | no | — | — |
| `30057` | Reserved | Reservado |  |  | 4 | — | no | — | — |
| `30058` | Temperature. Internal Inverter | Temperatura inversor | INT16 | [ºC x10] | 4 | Inversor | sí | normal | `sensor.inversor_0_temperatura` |
| `30059` | Reserved | Reservado |  |  | 4 | — | no | — | — |
| `30060` | Positive Isolation Resistance | Resistencia aislamiento (+) | UINT16 | [kOhm] | 4 | Inversor | sí | slow | `sensor.inversor_0_resistencia_de_aislamiento_positiva` |
| `30061` | Negative Isolation Resistance | Resistencia aislamiento (-) | UINT16 | [kOhm] | 4 | Inversor | sí | slow | `sensor.inversor_0_resistencia_de_aislamiento_negativa` |
| `30062` | RMS Differential Current | Corriente diferencial | UINT16 | [mA x10] | 4 | Inversor | no | — | — |
| `30063` | Digital Output 1. Status | Estado DO1 | UINT16 | [0: OFF, 1:ON] | 4 | Inversor | no | — | — |
| `30064` | Digital Output 2. Status | Estado DO2 | UINT16 | [0: OFF, 1:ON] | 4 | Inversor | no | — | — |
| `30065` | Digital Input DRM0. Status | Estado DRM0 | UINT16 | [0: OFF, 1:ON] | 4 | Inversor | no | — | — |
| `30066` | Digital Input 2. Status | Estado DI2 | UINT16 | [0: OFF, 1:ON] | 4 | Inversor | no | — | — |
| `30067` | Digital Input 3. Status | Estado DI3 | UINT16 | [0: OFF, 1:ON] | 4 | Inversor | no | — | — |
| `30068` | Reserved for Ingeteam | Reservado |  |  | 4 | — | no | — | — |
| `30069` | Battery. BMS Flags | Flags BMS | UINT16 | [Note 10] | 4 | Batería | sí | fast | `binary_sensor.bateria_0_carga_bloqueada`<br>`binary_sensor.bateria_0_descarga_bloqueada`<br>`binary_sensor.bateria_0_carga_forzada_por_el_bms`<br>`binary_sensor.bateria_0_calibracion_de_soc_pendiente`<br>`binary_sensor.bateria_0_carga_forzada_por_soc_bajo` |
| `30070` | External Wattmeter Grid. Voltage | Tensión vatímetro red | UINT16 | [V] | 4 | Red | sí | instant | `sensor.red_0_tension` |
| `30071` | External Wattmeter Grid. Frequency | Frecuencia vatímetro red | UINT16 | [Hz x10] | 5 | Red | sí | instant | `sensor.red_0_frecuencia` |
| `30072` | External Wattmeter Grid. Active Power | Potencia vatímetro red | INT16 | [W] | 5 | Red | sí | instant | `sensor.red_0_potencia` |
| `30073` | External Wattmeter Grid. Reactive Power | Reactiva vatímetro red | INT16 | [Var] | 5 | Red | no | — | — |
| `30074` | Battery. BMS Warnings | Avisos BMS | UINT16 | [Note 11] | 5 | Batería | no | — | — |
| `30075` | Battery. BMS Errors | Errores BMS | UINT16 | [Note 11] | 5 | Batería | no | — | — |
| `30076` | Battery. BMS Faults | Fallos BMS | UINT16 | [Note 11] | 5 | Batería | no | — | — |
| `30077` | Battery. BMS Protections | Protecciones BMS | UINT16 | [Note 11] | 5 | Batería | no | — | — |
| `30078` | Battery. Charge Limitation Reason | Motivo límite carga | UINT16 | [Note 9] | 5 | Batería | sí | normal | `sensor.bateria_0_motivo_de_limitacion_de_carga` |
| `30079` | Total Loads. Active Power (Critical + No Critical) | Potencia cargas totales | UINT16 | [W] | 5 | Consumo | sí | fast | `sensor.consumo_0_potencia` |
| `30080` | External PV. Power (Ingeteam Inverters) | Potencia FV externa | UINT16 | [W] | 5 | Campo solar | sí | fast | `sensor.campo_solar_0_potencia_fv_externa` |
| `30081` | EV Charger. Active Power | Potencia cargador VE | INT16 | [W] | 5 | Cargador VE | sí | fast | `sensor.cargador_ve_0_potencia` |

## Tier y activación de las entidades de diagnóstico

Reparto de `ingeteam.oneplay_storage` con un dispositivo por componente
([spec setup-flow-v2](../../../../changes/2026-10-04-setup-flow-v2/spec.md), §5.1 y §5.3). Hoy todas las extras van al tier lento y desactivadas
(`custom_components/modbus_solar/profiles/ingeteam/oneplay_storage.py:82-93`).

Reglas:

- Medidas eléctricas y alarmas: `fast` (10 s). Medidas: potencia activa y reactiva, factor de potencia,
  tensión, corriente y frecuencia. Las energías calculadas siguen a su potencia, que ya está en `fast`. Los bits
  del BMS avisan en segundos.
- `instant` (5 s) queda para la red principal (30070-30072, setup-flow-v2 §5.8), con sus energías. Ninguna
  entidad de diagnóstico va en `instant`: el dispositivo admite una petición por segundo entre todos los tiers.
- Temperatura del inversor, ratio y motivos de limitación: `normal` (60 s).
- Contador de horas, aislamiento y consigna de reactiva: `slow` (1 h).
- Las medidas de Vatímetro interno, Cargas críticas y Cargador VE salen activadas y sin categoría de diagnóstico:
  quien elige el componente quiere ver sus datos. Los bits del BMS salen activados y en diagnóstico. El resto
  sigue desactivado y en diagnóstico.

| Componente | Entidad | Registro | Hoy | Propuesta | Activada | Diagnóstico |
|---|---|---|---|---|---|---|
| Inversor | `operation_time` | 30007 | slow | slow | no | sí |
| Inversor | `reactive_power` | 30039 | slow | fast | no | sí |
| Inversor | `power_factor` | 30040 | slow | fast | no | sí |
| Inversor | `power_reduction_ratio` | 30041 | slow | normal | no | sí |
| Inversor | `power_reduction_reason` | 30042 | slow | normal | no | sí |
| Inversor | `reactive_setpoint_type` (nueva, Nota 8) | 30043 | — | slow | no | sí |
| Inversor | `dc_bus_voltage` | 30055 | slow | fast | no | sí |
| Inversor | `inverter_temperature` | 30058 | slow | normal | no | sí |
| Inversor | `isolation_positive` | 30060 | slow | slow | no | sí |
| Inversor | `isolation_negative` | 30061 | slow | slow | no | sí |
| Campo solar | `external_pv_power` | 30080 | slow | fast | no | sí |
| Batería | `battery_discharge_limit_reason` | 30030 | slow | normal | no | sí |
| Batería | `battery_charge_limit_reason` | 30078 | slow | normal | no | sí |
| Batería | 9 alarmas del BMS (Nota 4) | 30029 | — | fast | sí | sí |
| Batería | 5 flags del BMS (Nota 10) | 30069 | — | fast | sí | sí |
| Vatímetro interno | `internal_meter_voltage` | 30049 | slow | fast | sí | no |
| Vatímetro interno | `internal_meter_current` | 30050 | slow | fast | sí | no |
| Vatímetro interno | `internal_meter_frequency` | 30051 | slow | fast | sí | no |
| Vatímetro interno | `internal_meter_power` | 30052 | slow | fast | sí | no |
| Cargas críticas | `critical_load_voltage` | 30044 | slow | fast | sí | no |
| Cargas críticas | `critical_load_current` | 30045 | slow | fast | sí | no |
| Cargas críticas | `critical_load_frequency` | 30046 | slow | fast | sí | no |
| Cargas críticas | `critical_load_power` | 30047 | slow | fast | sí | no |
| Cargador VE | `ev_charger_power` | 30081 | slow | fast | sí | no |

Con todos los componentes, las entidades del perfil quedan así: instant 3 (las de red), más 2 energías; fast 34
(7 principales + 13 de esta tabla + 14 bits), más 3 energías y 2 controles; normal 12 (7 principales + 5); slow 6
(2 principales + 4), de ellas 4 desactivadas. Las principales de hoy no cambian de tier, salvo las de red.

Red no tiene entidades de diagnóstico ni alarmas: las alarmas del inversor (30010-30015, Nota 1) necesitan
`ABH2010IMC14`, que no está en el repo.

## Notas del PDF (págs. 6-8)

Nota 1: códigos de parada, alarmas y `Code 1-3` en `ABH2010IMC14` (guía de alarmas).

Nota 2, `Inverter Status` (30016):

| Valor | Descripción |
|---|---|
| 0 | Inverter Stopped |
| 1 | Starting |
| 2 | Off-grid |
| 3 | On-grid |
| 4 | On-grid (Standby Battery) |
| 5 | Waiting to connect to Grid |
| 6 | Critical Loads Bypassed to Grid |
| 7 | Emergency Charge from PV |
| 8 | Emergency Charge from Grid |
| 9 | Inverter Locked waiting for Reset |
| 10 | Error Mode |

Nota 3, `Battery. Status` (30027):

| Valor | Descripción |
|---|---|
| 0 | Standby |
| 1 | Discharging |
| 2 | Constant Current Charging |
| 3 | Constant Voltage Charging |
| 4 | Floating |
| 5 | Equalizing |
| 6 | Error Communication with BMS |
| 7 | No Configured |
| 8 | Capacity Calibration (Step 1) |
| 9 | Capacity Calibration (Step 2) |
| 10 | Standby Manual |

Nota 5: potencia reactiva positiva = corriente retrasada respecto a la tensión.
Nota 6: el coseno de φ va en valor absoluto; el signo sale de la reactiva.

Notas 7, 8 y 9: las columnas `es` y `en` son los textos que muestra la integración, con el código delante
(propuesta, [spec reason-labels](../../../../changes/2026-10-04-reason-labels/spec.md)).

Nota 7, `Active Power Reduction Reason` (30042):

| Valor | PDF | es | en |
|---|---|---|---|
| 0 | No limitation | 0 - Sin limitación | 0 - No limitation |
| 1 | Communication | 1 - Consigna por comunicación | 1 - Set-point via communication |
| 2 | PCB Temperature | 2 - Temperatura de la placa | 2 - PCB temperature |
| 3 | Heat Sink Temperature | 3 - Temperatura del disipador | 3 - Heat sink temperature |
| 4 | Pac vs Fac Algorithm | 4 - Algoritmo P-f (frecuencia de red) | 4 - P-f algorithm (grid frequency) |
| 5 | Soft Start | 5 - Arranque suave | 5 - Soft start |
| 6 | Charge Power Configured | 6 - Potencia de carga configurada | 6 - Configured charge power |
| 7 | PV Surplus injected to the Loads | 7 - Excedente FV a cargas | 7 - PV surplus to loads |
| 8 | Pac vs Vac Algorithm | 8 - Algoritmo P-V (tensión de red) | 8 - P-V algorithm (grid voltage) |
| 9 | Battery Power Limited | 9 - Potencia de batería limitada | 9 - Battery power limited |
| 10 | AC Grid Power Limited | 10 - Potencia de red limitada | 10 - AC grid power limited |
| 11 | Self-Consumption Mode | 11 - Modo autoconsumo | 11 - Self-consumption mode |
| 12 | High Bus Voltage Protection | 12 - Protección por tensión alta del bus | 12 - High bus voltage protection |
| 13 | LVRT or HVRT Process | 13 - Hueco o sobretensión de red (LVRT/HVRT) | 13 - Grid voltage dip or swell (LVRT/HVRT) |
| 14 | Nominal AC Current | 14 - Corriente AC nominal | 14 - Nominal AC current |
| 15 | Grid Consumption Protection | 15 - Protección de consumo de red | 15 - Grid consumption protection |
| 16 | PV Surplus Injected to the Grid | 16 - Excedente FV a red | 16 - PV surplus to grid |

Nota 8, `Reactive Power Set-Point Type` (30043):

| Valor | PDF | es | en |
|---|---|---|---|
| 0 | Cos() Configuration | 0 - Cos φ por configuración | 0 - Cos φ by configuration |
| 1 | Qac Communication | 1 - Q por comunicación | 1 - Q by communication |
| 2 | Cos() Communication | 2 - Cos φ por comunicación | 2 - Cos φ by communication |
| 3 | Qac vs Vac Algorithm | 3 - Algoritmo Q-V | 3 - Q-V algorithm |
| 4 | Cos() vs Pac Algorithm | 4 - Algoritmo cos φ-P | 4 - Cos φ-P algorithm |

Nota 9, `Battery. Discharge Limitation Reason` (30030) y `Battery. Charge Limitation Reason` (30078):

| Valor | PDF | es | en |
|---|---|---|---|
| 0 | No limitation | 0 - Sin limitación | 0 - No limitation |
| 1 | Heat Sink Temperature | 1 - Temperatura del disipador | 1 - Heat sink temperature |
| 2 | PT100 Temperature | 2 - Temperatura de la batería (PT100) | 2 - Battery temperature (PT100) |
| 3 | Low Bus Voltage Protection | 3 - Protección por tensión baja del bus | 3 - Low bus voltage protection |
| 4 | Battery Settings | 4 - Ajustes de la batería | 4 - Battery settings |
| 5 | BMS Communication | 5 - Comunicación con el BMS | 5 - BMS communication |
| 6 | SOC Max Configured | 6 - SOC máximo configurado | 6 - Configured maximum SOC |
| 7 | SOC Min Configured | 7 - SOC mínimo configurado | 7 - Configured minimum SOC |
| 8 | Maximum Battery Power | 8 - Potencia máxima de la batería | 8 - Maximum battery power |
| 9 | Modbus Command | 9 - Comando Modbus | 9 - Modbus command |
| 10 | Digital Input 2 | 10 - Entrada digital 2 | 10 - Digital input 2 |
| 11 | Digital Input 3 | 11 - Entrada digital 3 | 11 - Digital input 3 |
| 12 | PV charging scheduling | 12 - Programación de carga FV | 12 - PV charging schedule |
| 13 | EMS Strategy | 13 - Estrategia EMS | 13 - EMS strategy |

Notas 4, 10 y 11 (bits de BMS y códigos del fabricante de la batería): ver PDF págs. 6-8.
