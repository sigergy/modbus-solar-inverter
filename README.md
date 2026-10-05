# Modbus Solar

Custom integration de Home Assistant para inversores solares por Modbus TCP.
Usa la conexión compartida de la integración `modbus` del core.

## Equipos soportados

| Marca | Modelo | Entidades |
|---|---|---|
| Ingeteam | INGECON SUN STORAGE 1Play TL M | inversor, FV, batería (con las alarmas y estados del BMS), red y consumo; energía solar, de red y de batería calculada por la integración; switch y límite de vertido a red |
| Ingeteam | INGECON SUN 1Play TL M (sin storage) | estado del inversor, potencia activa, energía total |
| Ingenieurbüro Mencke & Tegtmeyer | Si-RS485TC-T-MB, -2T-MB, -2T-v-MB, -T-Tm-MB (sensor de irradiancia, vía pasarela RS485 → Modbus TCP) | irradiancia, velocidad del viento, temperatura de la célula y temperatura externa |

## Requisitos

- Home Assistant 2026.9.0 o posterior.
- El equipo accesible por Modbus TCP. Ingeteam recomienda un único cliente Modbus y al menos 1 s entre peticiones; en el STORAGE, además, no más de 10 registros por petición.

## Instalación

1. HACS → Integraciones → menú → Repositorios personalizados.
2. Añadir `https://github.com/sigergy/modbus-solar-inverter`, categoría «Integration».
3. Instalar «Modbus Solar» y reiniciar Home Assistant.

## Configuración

1. Ajustes → Dispositivos y servicios → Añadir integración → «Modbus Solar».
2. Elegir la marca y el modelo. Para un STORAGE, «Ingeteam · STORAGE 1Play TL M».
3. Escribir la IP o el nombre de host del equipo. Puerto e ID de unidad van en «Avanzado».
   La integración prueba la conexión antes de seguir.
4. Marcar los componentes que tiene el equipo (vatímetro interno, cargas críticas, cargador VE...).
5. Revisar las lecturas y escribir el nombre, el Device ID y, si se quiere, el número de serie.
6. Ajustar los intervalos de sondeo. La integración avisa si piden más de una petición por segundo.
   Se crea una entrada por equipo: para otro equipo, repetir desde el paso 1.
7. «Reconfigurar» en la entrada cambia host, puerto, número de serie, Device ID, componentes e intervalos.

Cada componente del equipo sale como un dispositivo propio en Home Assistant.

Detalle: [docs/features/device-setup.md](docs/features/device-setup.md) y
[docs/features/monitoring.md](docs/features/monitoring.md).

## Fuentes externas

- [domotica.solar](https://domotica.solar/): publicó una copia del mapa de registros Modbus del
  INGECON SUN STORAGE 1Play TL M ([registros_ingeteam.pdf](https://domotica.solar/wp-content/uploads/2021/07/registros_ingeteam.pdf)).
  Gracias por compartirla.
- Ingeteam, «INGECON SUN STORAGE 1Play TL M. Input registers» (`ABH2010IMB08`): la rev. _D es la
  copia de domotica.solar; el perfil sigue la rev. _I oficial. Ambas en
  [docs/wiki/brands/ingeteam/storage-1-play-tl-m/](docs/wiki/brands/ingeteam/storage-1-play-tl-m/).

El resto de documentos de fabricante y su procedencia: [docs/wiki/brands/ingeteam/README.md](docs/wiki/brands/ingeteam/README.md).

## Licencia

[GNU AGPL-3.0](LICENSE)
