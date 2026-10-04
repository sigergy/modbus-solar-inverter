# Ingeteam: documentación Modbus

Solo PDF oficiales y públicos de Ingeteam (ADR 0006).

| Fichero | Documento | Revisión | SHA-256 | Obtenido |
|---|---|---|---|---|
| `AAA0030IMB03_N.pdf` | Comandos Modbus, genérico de marca (original `Write_REG_Modbus_1P-Storage-AAA0030IMB03_.pdf`) | N, 20/05/24 | `b53eb0c3ad36230365833a798429e1e0d3be3ed8488e361fb70ceb1ee4c1d332` | 2026-10-04 |
| `AAX2023IPD02_E.pdf` | Guía técnica «Comunicación local y remota», genérica INGECON SUN (obtenido de `ingeras.es/archive/manuals/AAX2023/IPD02/`) | IPD02, 09/12/2025 | `9ee49a6adf70596ed41ef44c3d7aedf9dc9c0ba58c53ee19bcf7601a5a6c1c1f` | 2026-10-04 |
| `1-play-tl-m/ACL2010IMB05.pdf` | Input registers 1Play Storage (original `Input_REG_Modbus_1P-Storage-ACL2010IMB05_.pdf`) | IMB05 | `c0e6533edbd194974aba3e9fc3f040a65e009cabdd143aea6a02e6b2578620d4` | 2026-10-04 |

- La revisión F de AAA0030IMB03 (09/02/18) es anterior y se descarta.
- Falta `ACL0000IMC01` (estados y eventos). Se pide a Ingeteam. Según el manual `ACL2012IQM01` (INGECON SUN TL M2, apdo. 13.3) se descarga de www.ingeconsuntraining.info.
- Clientes Modbus: `ACL2010IMB05` (pág. 4) recomienda un único cliente y ≥ 1 s entre peticiones; `AAX2023IPD02` (pág. 7) admite varios clientes simultáneos en el puerto 502. Los 100 ms entre peticiones de `AAX2023IPD02` son solo para inversores Legacy por RS-485 (apdo. 3.1.1).
- Tabla de registros extraída: [1-play-tl-m/registers.md](1-play-tl-m/registers.md).
