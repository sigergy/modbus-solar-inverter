# Modbus Solar

Integración personalizada de Home Assistant para equipos solares por Modbus TCP.
Usa la conexión compartida de la integración `modbus` del core.

## Equipos soportados

| Marca | Modelo | Perfil | Entidades |
|---|---|---|---|
| Ingeteam | INGECON SUN STORAGE 1Play TL M | `ingeteam.oneplay_storage` | inversor, FV, batería (+ alarmas BMS), red, consumo, cargas críticas, vatímetro interno, cargador VE; energías calculadas |
| Ingeteam | INGECON SUN 1Play TL M (sin storage) | `ingeteam.oneplay` | estado, potencia activa, energía total |
| Mencke & Tegtmeyer | Si-RS485TC-T-MB, -2T-MB, -2T-v-MB, -T-Tm-MB (vía pasarela RS485 → TCP) | `mencke_tegtmeyer.si_rs485` | irradiancia, viento, temperatura de célula y externa |

## Funciones

- **Un equipo = una entrada.** Cada componente sale como un dispositivo propio.
- **Sondeo por tiers.** `instant` 5 s · `fast` 10 s · `normal` 60 s · `slow` 3600 s. Ajustables.
- **Presupuesto de peticiones.** Avisa si los intervalos piden más de 1 petición/s.
- **Medición de red** (STORAGE). Elige qué vatímetro mide la red:

  | Modo | Vatímetro | Dispositivo |
  |---|---|---|
  | Consumos en Grid (defecto) | externo | Red |
  | Consumos en Cargas Críticas | interno | Vatímetro interno |
  | Aislada | interno | Generador |

- **Energías calculadas** (STORAGE): solar, red importada/exportada, carga/descarga de batería.
  Listas para el panel de Energía.
- **Diagnostics.** Valor crudo y decodificado de cada registro. Host y número de serie ocultos.
- **Control de vertido** (STORAGE): implementado pero desactivado (`EXPORT_CONTROL_ENABLED = False`).
  Sin batería el inversor ignora el comando.

## Requisitos

- Home Assistant 2026.9.0 o posterior.
- Equipo accesible por Modbus TCP.
- Ingeteam: un único cliente Modbus, ≥ 1 s entre peticiones. STORAGE: ≤ 10 registros por petición.

## Instalación (HACS)

1. HACS → Integraciones → menú → Repositorios personalizados.
2. Añadir `https://github.com/sigergy/modbus-solar-inverter`, categoría «Integration».
3. Instalar «Modbus Solar» y reiniciar Home Assistant.

## Configuración

Ajustes → Dispositivos y servicios → Añadir integración → «Modbus Solar».

```
marca → modelo → conexión → medición de red* → componentes* → lecturas → nombre → intervalos
                    │                                            │
                    └─ sonda: prueba la conexión                 └─ volver a modelo / conexión
* solo si el perfil lo declara
```

| Paso | Qué se pide |
|---|---|
| conexión | host; puerto y unit ID en «Avanzado» |
| medición de red | modo de la tabla de arriba |
| componentes | vatímetro interno, cargas críticas, cargador VE... |
| lecturas | valores leídos, para cotejar con la pantalla del equipo |
| nombre | nombre, Device ID (va en el `entity_id`), número de serie opcional |
| intervalos | un intervalo por tier |

- Otro equipo: repetir el alta.
- «Reconfigurar» cambia conexión, Device ID, número de serie, medición de red, componentes e intervalos.
  Si cambia el Device ID, ofrece renombrar los `entity_id`.

Detalle: [device-setup](docs/features/device-setup.md) · [monitoring](docs/features/monitoring.md) · [control](docs/features/control.md).

## Arquitectura

Hexagonal. Contratos de capas comprobados con import-linter.

```
 raíz         __init__.py · config_flow.py        composición
                 │
 adapters     inbound (HA)  │  outbound (Modbus)  no se importan entre sí
                 │
 application  catálogo · sondeo · sonda · selección · control
                 │
 ports        DeviceGateway · DeviceWriter
                 │
 domain       tipos · perfil · decode/encode · energía · medición · validación

 profiles     datos de cada equipo; solo importan domain
```

```
custom_components/modbus_solar/
├── adapters/inbound/    config flow, coordinators, entidades, diagnostics
├── adapters/outbound/   ModbusGateway
├── application/         casos de uso
├── ports/               protocolos
├── domain/              lógica pura, sin HA ni Modbus
└── profiles/            ingeteam/, mencke_tegtmeyer/
```

Flujo de lectura:

```
TierCoordinator → read_tier → ModbusGateway.read → decode → TierResult → entidades
```

Añadir un equipo = añadir un perfil en `profiles/`. Detalle: [docs/architecture](docs/architecture/overview.md).

## Desarrollo

| Qué | Dónde |
|---|---|
| Entorno y lint (`scripts/lint.sh`) | [guides/setup](docs/guides/setup.md) |
| Tests (solo en GitHub Actions) | [guides/testing](docs/guides/testing.md) |
| Release | [guides/release](docs/guides/release.md) |
| Decisiones (ADR) | [docs/decisions](docs/decisions/) |
| Cambios | [CHANGELOG](CHANGELOG.md) |

## Fuentes externas

- [domotica.solar](https://domotica.solar/): publicó una copia del mapa de registros del STORAGE 1Play TL M
  ([registros_ingeteam.pdf](https://domotica.solar/wp-content/uploads/2021/07/registros_ingeteam.pdf)). Gracias.
- Ingeteam `ABH2010IMB08`: la rev. _D es la copia de domotica.solar; el perfil sigue la rev. _I oficial.
  Ambas en [docs/wiki/brands/ingeteam/storage-1-play-tl-m/](docs/wiki/brands/ingeteam/storage-1-play-tl-m/).
- Resto de documentos de fabricante: [docs/wiki/brands/ingeteam/README.md](docs/wiki/brands/ingeteam/README.md).

## Licencia

[GNU AGPL-3.0](LICENSE)
