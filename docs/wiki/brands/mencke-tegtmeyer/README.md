# Ingenieurbüro Mencke & Tegtmeyer: documentación Modbus

Solo PDF oficiales y públicos del fabricante (ADR 0006).

| Fichero | Documento | Revisión | SHA-256 | Obtenido |
|---|---|---|---|---|
| `si-rs485-mb/Specification_Si-RS485_MODBUS.pdf` | Especificación Modbus de la serie Si-RS485TC-…-MB: registros, función 0x46 y registros activos por modelo (original `Igmt Irradiance Sensor - Specification_Si-RS485_MODBUS.pdf`) | feb 2022, firmware 2.01 | `689d0c20131150fe86f0b1e6e199643828538a75e46f6864a6fc6fa9ee1255fa` | 2026-10-04 |
| `si-rs485-mb/Si_Instruction_digital_2017_E_SP.pdf` | Guía rápida en español: modelos, sensores externos, valores de fábrica y cableado RS485 | el nombre dice 2017; el pie del PDF dice nov 2019 | `797d4cf9d0cb32ee09ae0f422ec3f8c75c052b40a236d025e94874a8e35c8d01` | 2026-10-04 |

- Origen de la descarga: sin registrar. Los PDF son del fabricante (pie de página: www.ib-mut.de), pero
  falta anotar la URL exacta. Pendiente.
- Discrepancia de fecha en la guía: 2017 en el nombre del fichero, nov 2019 en el pie del PDF. No afecta
  a ningún registro.
- Tabla de registros extraída: [si-rs485-mb/registers.md](si-rs485-mb/registers.md).
- Perfil: `custom_components/modbus_solar/profiles/mencke_tegtmeyer/si_rs485.py`.
