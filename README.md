# Modbus Solar

Custom integration de Home Assistant para inversores solares por Modbus TCP.
Usa la conexión compartida de la integración `modbus` del core.

## Equipos soportados

| Marca | Modelo | Entidades |
|---|---|---|
| Ingeteam | INGECON SUN STORAGE 1Play TL M | inversor, FV, batería, red y consumo; energía solar, de red y de batería calculada por la integración |
| Ingeteam | INGECON SUN 1Play TL M (sin storage) | estado del inversor, potencia activa, energía total |

## Requisitos

- Home Assistant 2026.9.0 o posterior.
- El equipo accesible por Modbus TCP. Ingeteam recomienda un único cliente Modbus y al menos 1 s entre peticiones; en el STORAGE, además, no más de 10 registros por petición.

## Instalación

1. HACS → Integraciones → menú → Repositorios personalizados.
2. Añadir `https://github.com/sigergy/modbus-solar-inverter`, categoría «Integration».
3. Instalar «Modbus Solar» y reiniciar Home Assistant.

## Configuración

1. Ajustes → Dispositivos y servicios → Añadir integración → «Modbus Solar».
2. Elegir la marca. Se crea una entrada por marca.
3. En la entrada, «Añadir equipo»: nombre, host, puerto, ID de unidad y modelo.
   Para un STORAGE, elegir el modelo «STORAGE 1Play TL M».
   La integración lee el estado del inversor antes de guardar.
4. «Reconfigurar» en el equipo cambia host, puerto e intervalos de sondeo.

Detalle: [docs/features/device-setup.md](docs/features/device-setup.md) y
[docs/features/monitoring.md](docs/features/monitoring.md).

## Licencia

[PolyForm Noncommercial License 1.0.0](LICENSE)
