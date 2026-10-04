# STORAGE 1Play TL M: input registers (ABH2010IMB08)

Extraído de `ABH2010IMB08.pdf` (revisión _I, 23/04/2025). Ante discrepancia, manda el PDF.
Escalas y orden de palabras de los registros de 32 bits sin verificar en equipo.

- Lectura con la función 0x04 (Read Input Registers), referencias 3xxxx (PDF pág. 9).
- El registro 30001 es la dirección 0 del protocolo: dirección = registro − 30001 (PDF pág. 9).
- `Página` es la página del PDF donde está la fila. Se omite la columna «Since FW Ver.».
- 30008 y 30012 no tienen fila propia en el PDF: son la segunda palabra de 30007 y 30011 (UINT32).
- El mapa no trae ningún contador de energía.
- El manual `ABH2014IQM01.pdf` (apdo. 19.6.1, pág. 50) recomienda un único cliente en el puerto 502,
  al menos 1 s entre peticiones y no más de 10 registros por petición.

| Registro | Nombre (PDF) | Tipo | Unidad / nota | Página |
|---|---|---|---|---|
| `30001` | Current Date. Year | UINT16 |  | 3 |
| `30002` | Current Date. Month | UINT16 |  | 3 |
| `30003` | Current Date. Day | UINT16 |  | 3 |
| `30004` | Current Date. Hour | UINT16 |  | 3 |
| `30005` | Current Date. Minute | UINT16 |  | 3 |
| `30006` | Current Date. Second | UINT16 |  | 3 |
| `30007` | Inverter. Total operation time | UINT32 | [h] | 3 |
| `30008` | (segunda palabra de 30007) |  |  | 3 |
| `30009` | Reserved for Ingeteam |  |  | 3 |
| `30010` | Stop Event | UINT16 | [Note 1] | 3 |
| `30011` | Alarms | UINT32 | [Note 1] | 3 |
| `30012` | (segunda palabra de 30011) |  |  | 3 |
| `30013` | Code 1 | UINT16 | [Note 1] | 3 |
| `30014` | Code 2 | UINT16 | [Note 1] | 3 |
| `30015` | Code 3 | UINT16 | [Note 1] | 3 |
| `30016` | Inverter Status | UINT16 | [Note 2] | 3 |
| `30017` | Waiting Time to Connect to Grid | UINT16 | [sec] | 3 |
| `30018` | Battery. Voltage | UINT16 | [V x 10] | 3 |
| `30019` | Battery. Current | INT16 | [A x 100] | 3 |
| `30020` | Battery. Power | INT16 | [W] | 3 |
| `30021` | Battery. SOC | UINT16 | [%] | 3 |
| `30022` | Battery. SOH | UINT16 | [%] | 3 |
| `30023` | Battery. Charging Voltage | UINT16 | [V x 10] | 3 |
| `30024` | Battery. Discharging Voltage | UINT16 | [V x 10] | 3 |
| `30025` | Battery. Max. Charging Current | UINT16 | [A x 100] | 3 |
| `30026` | Battery. Max. Discharging Current | UINT16 | [A x 100] | 3 |
| `30027` | Battery. Status | UINT16 | [Note 3] | 3 |
| `30028` | Battery. Temperature | INT16 | [ºC x 10] | 3 |
| `30029` | Battery. BMS Alarms | UINT16 | [Note 4] | 3 |
| `30030` | Battery. Discharge Limitation Reason | UINT16 | [Note 9] | 3 |
| `30031` | Battery. Voltage Internal Sensor | UINT16 | [V x 10] | 3 |
| `30032` | PV1. Voltage | UINT16 | [V] | 3 |
| `30033` | PV1. Current | UINT16 | [A x100] | 3 |
| `30034` | PV1. Power | UINT16 | [W] | 4 |
| `30035` | PV2. Voltage | UINT16 | [V] | 4 |
| `30036` | PV2. Current | UINT16 | [A x100] | 4 |
| `30037` | PV2. Power | UINT16 | [W] | 4 |
| `30038` | Inverter. Active Power | INT16 | [W] | 4 |
| `30039` | Inverter. Reactive Power | INT16 | [Var, Note 5] | 4 |
| `30040` | Inverter. Cosφ | INT16 | [x1000, Note 6] | 4 |
| `30041` | Active Power Reduction Ratio | UINT16 | [% x10] | 4 |
| `30042` | Active Power Reduction Reason | UINT16 | [Note 7] | 4 |
| `30043` | Reactive Power Set-Point Type | UINT16 | [Note 8] | 4 |
| `30044` | Critical Loads. Voltage | UINT16 | [V] | 4 |
| `30045` | Critical Loads. Current | UINT16 | [A x100] | 4 |
| `30046` | Critical Loads. Frequency | UINT16 | [Hz x100] | 4 |
| `30047` | Critical Loads. Active Power | INT16 | [W] | 4 |
| `30048` | Critical Loads. Reactive Power | INT16 | [Var, Note 5] | 4 |
| `30049` | Internal Wattmeter Grid. Voltage | UINT16 | [V] | 4 |
| `30050` | Internal Wattmeter Grid. Current | UINT16 | [A x100] | 4 |
| `30051` | Internal Wattmeter Grid. Frequency | UINT16 | [Hz x100] | 4 |
| `30052` | Internal Wattmeter Grid. Active Power | INT16 | [W] | 4 |
| `30053` | Internal Wattmeter Grid. Reactive Power | INT16 | [Var, Note 5] | 4 |
| `30054` | Internal Wattmeter Grid. Cosφ | INT16 | [x1000, Note 6] | 4 |
| `30055` | DC Bus Voltage | UINT16 | [V] | 4 |
| `30056` | Reserved |  |  | 4 |
| `30057` | Reserved |  |  | 4 |
| `30058` | Temperature. Internal Inverter | INT16 | [ºC x10] | 4 |
| `30059` | Reserved |  |  | 4 |
| `30060` | Positive Isolation Resistance | UINT16 | [kOhm] | 4 |
| `30061` | Negative Isolation Resistance | UINT16 | [kOhm] | 4 |
| `30062` | RMS Differential Current | UINT16 | [mA x10] | 4 |
| `30063` | Digital Output 1. Status | UINT16 | [0: OFF, 1:ON] | 4 |
| `30064` | Digital Output 2. Status | UINT16 | [0: OFF, 1:ON] | 4 |
| `30065` | Digital Input DRM0. Status | UINT16 | [0: OFF, 1:ON] | 4 |
| `30066` | Digital Input 2. Status | UINT16 | [0: OFF, 1:ON] | 4 |
| `30067` | Digital Input 3. Status | UINT16 | [0: OFF, 1:ON] | 4 |
| `30068` | Reserved for Ingeteam |  |  | 4 |
| `30069` | Battery. BMS Flags | UINT16 | [Note 10] | 4 |
| `30070` | External Wattmeter Grid. Voltage | UINT16 | [V] | 4 |
| `30071` | External Wattmeter Grid. Frequency | UINT16 | [Hz x10] | 5 |
| `30072` | External Wattmeter Grid. Active Power | INT16 | [W] | 5 |
| `30073` | External Wattmeter Grid. Reactive Power | INT16 | [Var] | 5 |
| `30074` | Battery. BMS Warnings | UINT16 | [Note 11] | 5 |
| `30075` | Battery. BMS Errors | UINT16 | [Note 11] | 5 |
| `30076` | Battery. BMS Faults | UINT16 | [Note 11] | 5 |
| `30077` | Battery. BMS Protections | UINT16 | [Note 11] | 5 |
| `30078` | Battery. Charge Limitation Reason | UINT16 | [Note 9] | 5 |
| `30079` | Total Loads. Active Power (Critical + No Critical) | UINT16 | [W] | 5 |
| `30080` | External PV. Power (Ingeteam Inverters) | UINT16 | [W] | 5 |
| `30081` | EV Charger. Active Power | INT16 | [W] | 5 |

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
Notas 4, 7, 8, 9, 10 y 11 (bits de BMS, motivos de limitación, consigna de reactiva): ver PDF págs. 6-8.
