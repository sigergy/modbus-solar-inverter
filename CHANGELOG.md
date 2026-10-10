# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

## [0.2.0] - 2026-10-10

Versión estable. Mismo código que 0.2.0b1.

## [0.2.0b1] - 2026-10-06

### Añadido

- STORAGE 1Play TL M: nuevo paso «Medición de red» en el alta y en reconfigurar. Dice qué vatímetro mide la red:
  «Consumos en Grid» (vatímetro externo, por defecto), «Consumos en Cargas Críticas» (vatímetro interno) o
  «Aislada».
- Sensores «Potencia de red» (lo que entra de la red) y «Potencia a la red» (lo que sale), en W.
- Modo «Aislada»: dispositivo nuevo «Generador» con su potencia y su energía, para el grupo electrógeno en las
  bornas de red.

### Cambiado

- Las energías importada y exportada salen del vatímetro que diga la medición de red. Antes salían siempre del
  vatímetro externo y sin él eran falsas. Una instalación anterior queda en «Consumos en Grid» y conserva su
  historial.
- El vatímetro elegido en la medición de red sale marcado en «Componentes» y no se puede desmarcar.
- Aviso: una instalación anterior sin «Red» en «Componentes» recupera el dispositivo Red, porque «Consumos en Grid»
  lo necesita. Si desmarcaste Red, reconfigura y elige «Consumos en Cargas Críticas».
- STORAGE 1Play TL M: el switch y el límite de vertido a red ya no se crean. Sin batería el inversor ignora el
  comando (CMD 26). El código sigue en el perfil, desactivado con `EXPORT_CONTROL_ENABLED = False`. Las entidades
  de una instalación anterior quedan sin uso: se borran al quitar y volver a añadir el equipo.

## [0.1.0] - 2026-10-05

Primera versión estable.

### Cambiado

- El nombre de los dispositivos ya no lleva el Device ID: «Red», «Inversor». El `entity_id` de las entidades nuevas
  sí lo lleva, como antes (`sensor.red_0_potencia`). Los `entity_id` ya creados no cambian.

## [0.1.0b6] - 2026-10-05

### Añadido

- Alta en más pasos: marca, modelo, conexión, componentes, lecturas, nombre y intervalos.
- Selección de componentes del equipo (vatímetro interno, cargas críticas, cargador VE...).
  Cada componente sale como un dispositivo propio en Home Assistant.
- Alarmas y estados del BMS de la batería como sensores binarios.
- Número de serie opcional, leído del equipo si el perfil lo permite.
- Reconfiguración de host, puerto, número de serie, Device ID, componentes e intervalos.
- Aviso si los intervalos piden más de una petición por segundo.

### Cambiado

- La red principal se lee cada 5 s (tier `instant`). Las medidas eléctricas pasan de 5 s a 10 s.
- El alta ya no tiene paso de confirmación.
