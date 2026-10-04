# Modbus Solar

Custom integration de Home Assistant para inversores solares por Modbus TCP.
Usa la conexión compartida de la integración `modbus` del core.

## Equipos soportados

| Marca | Modelo | Entidades |
|---|---|---|
| Ingeteam | INGECON SUN STORAGE 1Play TL M | inversor, FV, batería, red y consumo; energía solar, de red y de batería calculada por la integración; switch y límite de vertido a red |
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
2. Elegir el modelo. Para un STORAGE, «Ingeteam · STORAGE 1Play TL M».
3. Escribir la IP o el nombre de host del equipo. Puerto e ID de unidad van en «Avanzado».
   La integración prueba la conexión antes de seguir.
4. Revisar las lecturas del equipo y darle un nombre.
   Se crea una entrada por equipo: para otro equipo, repetir desde el paso 1.
5. «Reconfigurar» en la entrada cambia host, puerto e intervalos de sondeo.

Detalle: [docs/features/device-setup.md](docs/features/device-setup.md) y
[docs/features/monitoring.md](docs/features/monitoring.md).

## Licencia

[PolyForm Noncommercial License 1.0.0](LICENSE)
