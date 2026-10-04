# Si-RS485TC-…-MB: registros Modbus (Specification_Si-RS485_MODBUS)

Extraído de `Specification_Si-RS485_MODBUS.pdf` (feb 2022, firmware 2.01) y de
`Si_Instruction_digital_2017_E_SP.pdf`. Ante discrepancia, manda el PDF.
Las escalas no están verificadas en equipo.

- Modbus RTU, funciones 0x03 (Read Holding Register) y 0x04 (Read Input Register) (Specification pág. 1).
  El perfil usa la 0x04.
- Valores de fábrica: 9600 baudios, 8N1, dirección 1 (Specification pág. 1; la guía los repite).
- El sensor empieza a atender Modbus 4 s después del encendido (Specification pág. 1).
- Un registro opcional que el sensor no soporta devuelve 0, no un error (Specification pág. 1).
- **Los registros 7 y 8 exigen firmware ≥ 1.53** (Specification pág. 1).
- Para la integración, el sensor está detrás de una pasarela RS485 → Modbus TCP: la dirección Modbus es
  la del esclavo RS485 y el puerto es el de la pasarela.

## Registros usados por el perfil

| Registro | Valor | Tipo | Ganancia | Rango | Nota | Entidad | Página |
|---|---|---|---|---|---|---|---|
| `0000` | Irradiancia, W/m² | UINT16 | 0,1 | 0…1500 | hasta firmware 1.52 el rango es 0…1400 | `irradiance` | 1 |
| `0003` | Velocidad del viento, m/s | UINT16 | 0,1 | 0…80 | opcional | `wind_speed` | 1 |
| `0007` | Temperatura de la célula, °C | INT16 | 0,1 | -40…+90 | firmware ≥ 1.53 | `cell_temperature` | 1 |
| `0008` | Temperatura externa 1, °C | INT16 | 0,1 | -40…+90 | firmware ≥ 1.53; opcional | `external_temperature` | 1 |

## Registros no usados

| Registro | Motivo | Página |
|---|---|---|
| `0001`, `0002`, `0005`, `0006` | compatibilidad con firmwares viejos; `0002` y `0006` llevan offset (-25 y -100) | 2 |
| `0004` | reservado, valor 0 | 2 |
| `0009` | temperatura externa 2, solo firmware ≥ 2.01 | 1 |

Los huecos entre 0, 3, 7 y 8 existen y se leen sin error: por eso el perfil los agrupa en un solo bloque
FC04 de 9 registros (`max_gap=3`).

## Registros activos por modelo (Specification pág. 5)

| Serie de serie | Modelo | Registros activos |
|---|---|---|
| `485-1` | Si-RS485TC-T-MB | 0000, 0007 |
| `485-2` | Si-RS485TC-2T-MB | 0000, 0007, 0008 |
| `485-3` | Si-RS485TC-2T-v-MB | 0000, 0003, 0007, 0008 |
| `485-4` | Si-RS485TC-T-Tm-MB | 0000, 0007, 0008 |

Según la guía (`Si_Instruction_digital_2017_E_SP.pdf` pág. 1), el registro 0008 es la temperatura
ambiente en el `-2T` y la temperatura del módulo en el `-T-Tm`; por eso la entidad se llama
`external_temperature`. En los modelos que no tienen un registro, o con el sensor externo sin conectar,
la lectura es 0 y HA la muestra como medida.

## Fuera de alcance

- Función 0x46, subfunciones 07 y 08: versión de firmware y número de serie; subfunción 04:
  parámetros de comunicación (Specification págs. 3-5). `DeviceGateway` solo lee registros.

## Discrepancias entre documentos

- Baudios: la guía da 38400 como máximo; la especificación lista también 57600 sin que la tabla de la
  función 0x46 lo admita (Specification págs. 1 y 4). No afecta a la integración: la velocidad es la
  de la pasarela.
- Fecha de la guía: 2017 en el nombre del fichero, nov 2019 en el pie del PDF.
