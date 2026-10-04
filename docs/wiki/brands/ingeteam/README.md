# Ingeteam: documentación Modbus

PDF oficiales y públicos de Ingeteam (ADR 0006). Las copias de terceros van en su propia tabla y no son fuente (ADR 0014).

| Fichero | Documento | Revisión | SHA-256 | Obtenido |
|---|---|---|---|---|
| `AAA0030IMB03_N.pdf` | Comandos Modbus, genérico de marca (original `Write_REG_Modbus_1P-Storage-AAA0030IMB03_.pdf`) | N, 20/05/24 | `b53eb0c3ad36230365833a798429e1e0d3be3ed8488e361fb70ceb1ee4c1d332` | 2026-10-04 |
| `AAX2023IPD02_E.pdf` | Guía técnica «Comunicación local y remota», genérica INGECON SUN (obtenido de `ingeras.es/archive/manuals/AAX2023/IPD02/`) | IPD02, 09/12/2025 | `9ee49a6adf70596ed41ef44c3d7aedf9dc9c0ba58c53ee19bcf7601a5a6c1c1f` | 2026-10-04 |
| `AAA0060IMB05.pdf` | API HTTP de los inversores INGECON SUN: 1Play, 3Play, STORAGE 1Play TL M y STORAGE 3Play (obtenido de `ingeras.es/protocols/`) | A, 05/09/2023 | `380b6acafc54eabc11004ce06c729439c2cd3c8ccf257a25fe45f5e14886772c` | 2026-10-04 |
| `1-play-tl-m/ACL2010IMB05.pdf` | Datos de monitorización INGECON SUN 1PLAY/3PLAY, sin storage: holding 0x10xx, función 0x03 (original `Input_REG_Modbus_1P-Storage-ACL2010IMB05_.pdf`; pese al nombre, el PDF no cubre el STORAGE) | IMB05 | `c0e6533edbd194974aba3e9fc3f040a65e009cabdd143aea6a02e6b2578620d4` | 2026-10-04 |
| `storage-1-play-tl-m/ABH2010IMB08.pdf` | Input registers INGECON SUN STORAGE 1Play TL M: 30001-30081, función 0x04 (obtenido de `ingeras.es/manual/`) | _I, 23/04/2025 | `35af7fa3537c2b9679ca36a71eda811af647bed3c95e9d074de61f134fc0050c` | 2026-10-04 |
| `storage-1-play-tl-m/ABH2014IQM01.pdf` | Manual de instalación y uso INGECON SUN STORAGE 1Play TL M (obtenido de `ingeras.es/manual/`) | _I | `199be3dc1bfb2ba792a559a45c4f8cec18724fe2e54076eb23bc15d3d4cba1be` | 2026-10-04 |

Copias de terceros, no oficiales (ADR 0014):

| Fichero | Documento | Revisión | SHA-256 | Obtenido |
|---|---|---|---|---|
| `storage-1-play-tl-m/input_registers_ABH2010IMB08_D.pdf` | Input registers INGECON SUN STORAGE 1Play TL M, copia publicada por domotica.solar (original `registros_ingeteam.pdf`, de https://domotica.solar/wp-content/uploads/2021/07/registros_ingeteam.pdf) | _D, 17/05/2021 | `5474776c40431fc8fbb8aa09c585336ff8f4520d3df18e70ba1e0dc35c3245d9` | 2026-10-04 |

- `ABH2010IMB08_D` es anterior a la _I y su numeración va desplazada una posición (por ejemplo, «Battery. BMS Alarms» es 30030 en la _D y 30029 en la _I). Solo referencia: manda la _I.
- La revisión F de AAA0030IMB03 (09/02/18) es anterior y se descarta.
- Falta `ACL0000IMC01` (estados y eventos). Se pide a Ingeteam. Según el manual `ACL2012IQM01` (INGECON SUN TL M2, apdo. 13.3) se descarga de www.ingeconsuntraining.info.
- Clientes Modbus: `ACL2010IMB05` (pág. 4) recomienda un único cliente y ≥ 1 s entre peticiones; `AAX2023IPD02` (pág. 7) admite varios clientes simultáneos en el puerto 502. Los 100 ms entre peticiones de `AAX2023IPD02` son solo para inversores Legacy por RS-485 (apdo. 3.1.1).
- Clientes Modbus en el STORAGE 1Play TL M: `ABH2014IQM01` (apdo. 19.6.1, pág. 50) recomienda un único cliente en el puerto 502, ≥ 1 s entre peticiones y ≤ 10 registros por petición.
- Fuente de los documentos del STORAGE 1Play TL M: su página de soporte, https://training.ingeconsunvista.com/?page_id=2880.
- No se incluye `ABH2010IMC14` (alarmas, eventos y estados del STORAGE 1Play TL M, rev. _F): el PDF va marcado «Restricted Information». Se descarga de https://www.ingeras.es/manual/ABH2010IMC14.pdf.
- Tablas de registros extraídas:
  - 1Play/3Play sin storage: [1-play-tl-m/registers.md](1-play-tl-m/registers.md);
  - STORAGE 1Play TL M: [storage-1-play-tl-m/registers-storage-1-play-tl-m.md](storage-1-play-tl-m/registers-storage-1-play-tl-m.md).
- Vertido a red del STORAGE 1Play TL M: CMD 26, dato `0x0A` «Grid power» de `AAA0030IMB03_N` (págs. 7, 19-20). La potencia contratada («Hired Grid Power», `ABH2014IQM01` pág. 54) no tiene comando ni registro Modbus documentado.
