# 1Play Storage: input registers (ACL2010IMB05)

Extraído de `ACL2010IMB05.pdf`. Ante discrepancia, manda el PDF.
Escala `[X x 10]` y orden de palabras de los registros de 32 bits sin verificar en equipo:
se comprueban con diagnostics.

El PDF es bilingüe: la tabla en español está en las páginas 4 a 7 y la inglesa, con los mismos
registros, en las páginas 11 a 14. Esta tabla sigue la española. `Página` es la página del PDF
donde está la fila. Los registros son holding de solo lectura (función 0x03, PDF pág. 4).

| Dirección | Nombre (PDF) | Tipo | Unidad | Página | Notas |
|---|---|---|---|---|---|
| `0x1001` | Vac1 | UINT16 | [V x 10] | 4 |  |
| `0x1002` | Iac1 | UINT16 | [A x 100] | 4 |  |
| `0x1003` | Pac1 | INT32 | [W x 10] | 4 |  |
| `0x1005` | Frecuencia1 | UINT16 | [Hz x 100] | 4 |  |
| `0x1006` | Vac2 | UINT16 | [V x 10] | 4 |  |
| `0x1007` | Iac2 | UINT16 | [A x 100] | 4 |  |
| `0x1008` | Pac2 | INT32 | [W x 10] | 4 |  |
| `0x100A` | Frecuencia2 | UINT16 | [Hz x 100] | 4 |  |
| `0x100B` | Vac3 | UINT16 | [V x 10] | 4 |  |
| `0x100C` | Iac3 | UINT16 | [A x 100] | 4 |  |
| `0x100D` | Pac3 | INT32 | [W x 10] | 4 |  |
| `0x100F` | Frecuencia3 | UINT16 | [Hz x 100] | 4 |  |
| `0x1010` | Vmppt1 | UINT16 | [V x 10] | 5 |  |
| `0x1011` | Imppt1 | INT16 | [A x 100] | 5 |  |
| `0x1012` | Pmppt1 | UINT32 | [W x 10] | 5 |  |
| `0x1014` | Vmppt2 | UINT16 | [V x 10] | 5 |  |
| `0x1015` | Imppt2 | INT16 | [A x 100] | 5 |  |
| `0x1016` | Pmppt2 | UINT32 | [W x 10] | 5 |  |
| `0x1018` | Vmppt3 | UINT16 | [V x 10] | 5 |  |
| `0x1019` | Imppt3 | INT16 | [A x 100] | 5 |  |
| `0x101A` | Pmppt3 | UINT32 | [W x 10] | 5 |  |
| `0x101C` | Temperatura interna | INT16 | [ºC] | 5 |  |
| `0x101D` | Estado del inversor | UINT16 | - | 5 | Nota 3 |
| `0x101E` | Código de Evento 1 | UINT16 | - | 5 | Nota 1 |
| `0x101F` | Código de Evento 2 | UINT16 | - | 5 | Nota 1 |
| `0x1020` | Código de Evento 3 | UINT16 | - | 5 | Nota 1 |
| `0x1021` | Energía total | UINT32 | [Wh x 10] | 5 |  |
| `0x1023` | Tiempo de generación | UINT32 | [Horas] | 5 |  |
| `0x1025-0x1036` | Reservado | - | - | 5 |  |
| `0x1037` | P potencia activa total de salida | INT32 | [W x 10] | 5 |  |
| `0x1039` | Q potencia reactiva total de salida | INT32 | [Q x 10] | 5 | Nota 2 |
| `0x103B` | Potencia pico de generación | UINT32 | [W x 10] | 5 |  |
| `0x103D` | Coseno de Phi | INT16 | [PF x 1000] | 5 |  |
| `0x103E` | Vmppt4 | UINT16 | [V x 10] | 5 |  |
| `0x103F` | Imppt4 | INT16 | [A x 100] | 5 |  |
| `0x1040` | Pmppt4 | UINT32 | [W x 10] | 5 |  |
| `0x1041-0x1050` | Reservado | - | - | 5 |  |
| `0x1051` | Istring1 | INT16 | [A x 100] | 5 |  |
| `0x1052` | Vstring1 | UINT16 | [V x 10] | 5 |  |
| `0x1053` | Istring2 | INT16 | [A x 100] | 5 |  |
| `0x1054` | Vstring2 | UINT16 | [V x 10] | 5 |  |
| `0x1055` | Istring3 | INT16 | [A x 100] | 5 |  |
| `0x1056` | Vstring3 | UINT16 | [V x 10] | 5 |  |
| `0x1057` | Istring4 | INT16 | [A x 100] | 5 |  |
| `0x1058` | Vstring4 | UINT16 | [V x 10] | 5 |  |
| `0x1059` | Istring5 | INT16 | [A x 100] | 5 |  |
| `0x105A` | Vstring5 | UINT16 | [V x 10] | 5 |  |
| `0x105B` | Istring6 | INT16 | [A x 100] | 5 |  |
| `0x105C` | Vstring6 | UINT16 | [V x 10] | 6 |  |
| `0x105D` | Istring7 | INT16 | [A x 100] | 6 |  |
| `0x105E` | Vstring7 | UINT16 | [V x 10] | 6 |  |
| `0x105F` | Istring8 | INT16 | [A x 100] | 6 |  |
| `0x1060` | Vstring8 | UINT16 | [V x 10] | 6 |  |
| `0x1061` | Istring9 | INT16 | [A x 100] | 6 |  |
| `0x1062` | Vstring9 | UINT16 | [V x 10] | 6 |  |
| `0x1063` | Istring10 | INT16 | [A x 100] | 6 |  |
| `0x1064` | Vstring10 | UINT16 | [V x 10] | 6 |  |
| `0x1065` | Istring11 | INT16 | [A x 100] | 6 |  |
| `0x1066` | Vstring11 | UINT16 | [V x 10] | 6 |  |
| `0x1067` | Istring12 | INT16 | [A x 100] | 6 |  |
| `0x1068` | Vstring12 | UINT16 | [V x 10] | 6 |  |
| `0x1069` | Istring13 | INT16 | [A x 100] | 6 |  |
| `0x1069` | Istring13 | INT16 | [A x 100] | 6 |  |
| `0x106A` | Vstring13 | UINT16 | [V x 10] | 6 |  |
| `0x106B` | Istring14 | INT16 | [A x 100] | 6 |  |
| `0x106C` | Vstring14 | UINT16 | [V x 10] | 6 |  |
| `0x106D` | Istring15 | INT16 | [A x 100] | 6 |  |
| `0x106E` | Vstring15 | UINT16 | [V x 10] | 6 |  |
| `0x106F` | Istring16 | INT16 | [A x 100] | 6 |  |
| `0x1070` | Vstring16 | UINT16 | [V x 10] | 6 |  |
| `0x1071` | Istring17 | INT16 | [A x 100] | 6 |  |
| `0x1072` | Vstring17 | UINT16 | [V x 10] | 6 |  |
| `0x1073` | Istring18 | INT16 | [A x 100] | 6 |  |
| `0x1074` | Vstring18 | UINT16 | [V x 10] | 6 |  |
| `0x1074 - 0x107F` | Reservado | - | - | 6 |  |
| `0x1080` | Vmppt5 | UINT16 | [V x 10] | 6 |  |
| `0x1081` | Imppt5 | INT16 | [A x 100] | 6 |  |
| `0x1082` | Pmppt5 | UINT32 | [W x 10] | 6 |  |
| `0x1084` | Vmppt6 | UINT16 | [V x 10] | 6 |  |
| `0x1085` | Imppt6 | INT16 | [A x 100] | 6 |  |
| `0x1086` | Pmppt6 | UINT32 | [W x 10] | 6 |  |
| `0x1088` | Vmppt7 | UINT16 | [V x 10] | 6 |  |
| `0x1089` | Imppt7 | INT16 | [A x 100] | 6 |  |
| `0x108A` | Pmppt7 | UINT32 | [W x 10] | 6 |  |
| `0x108C` | Vmppt8 | UINT16 | [V x 10] | 6 |  |
| `0x108D` | Imppt8 | INT16 | [A x 100] | 6 |  |
| `0x108E` | Pmppt8 | UINT32 | [W x 10] | 7 |  |
| `0x1090` | Vmppt9 | UINT16 | [V x 10] | 7 |  |
| `0x1091` | Imppt9 | INT16 | [A x 100] | 7 |  |
| `0x1092` | Pmppt9 | UINT32 | [W x 10] | 7 |  |

## Notas del PDF

Texto de las notas de la página 7, literal. Las referencias `[Nota N]` aparecen en la columna de
unidad del PDF; aquí pasan a `Notas`, y `Unidad` queda en `-` si el PDF no da otra unidad.

**Nota 1:** Más información en el documento ACL0000IMC01 de descripción de estados y eventos.

**Nota 2:** Criterio de signos para la potencia reactiva.

| Tipo de corriente | Efecto en la red | Signo de reactiva | Signo de tangente/coseno | Diagrama fasorial |
|---|---|---|---|---|
| La corriente está retrasada con respecto a la tensión. | Aumento de la tensión de red. | Q > 0 | Positivo | (imagen, no transcrita) |
| La corriente está adelantada con respecto a la tensión. | Disminución de la tensión de red | Q < 0 | Negativo | (imagen, no transcrita) |

**Nota 3:** Estado de inversor.

| Value | Description |
|---|---|
| 0x0 | Estado por defecto de fábrica |
| 0x1 | Inversor desconectado de red. |
| 0x3 | Inversor conectado a red. |

## Particularidades del PDF

Copiadas tal cual, sin corregir:

- La fila `0x1069` (`Istring13`) aparece dos veces seguidas en la página 6.
- `0x1074` aparece como `Vstring18` y también como inicio del rango reservado `0x1074 - 0x107F`.
