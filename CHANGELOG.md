# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

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
