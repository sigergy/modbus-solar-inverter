# Modbus Solar

Custom integration de Home Assistant para inversores solares por Modbus TCP.
Usa la conexión compartida de la integración `modbus` del core.

## Equipos soportados

| Marca | Modelo | Entidades |
|---|---|---|
| Ingeteam | 1Play Storage | estado del inversor, potencia activa, energía total |

## Requisitos

- Home Assistant 2026.9.0 o posterior.
- El equipo accesible por Modbus TCP. El Ingeteam admite un solo cliente Modbus a la vez.

## Instalación

1. HACS → Integraciones → menú → Repositorios personalizados.
2. Añadir `https://github.com/sigergy/modbus-solar-inverter`, categoría «Integration».
3. Instalar «Modbus Solar» y reiniciar Home Assistant.

## Configuración

1. Ajustes → Dispositivos y servicios → Añadir integración → «Modbus Solar».
2. Elegir la marca. Se crea una entrada por marca.
3. En la entrada, «Añadir equipo»: nombre, host, puerto, ID de unidad y modelo.
   La integración lee el estado del inversor antes de guardar.
4. «Reconfigurar» en el equipo cambia host, puerto e intervalos de sondeo.

Detalle: [docs/features/device-setup.md](docs/features/device-setup.md) y
[docs/features/monitoring.md](docs/features/monitoring.md).

## Licencia

[PolyForm Noncommercial License 1.0.0](LICENSE)
