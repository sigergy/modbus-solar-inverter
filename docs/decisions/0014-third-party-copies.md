---
status: accepted
date: 2026-10-04
---

# 0014 — Copias de terceros como referencia, nunca como fuente

## Contexto

ADR 0006 solo admite en `docs/wiki/brands/` PDF oficiales y públicos.

domotica.solar publica una copia del mapa de input registers del STORAGE 1Play TL M (`ABH2010IMB08`, rev. _D, 17/05/2021): https://domotica.solar/wp-content/uploads/2021/07/registros_ingeteam.pdf. Es anterior a la rev. _I del repo y su numeración va desplazada una posición (por ejemplo, «Battery. BMS Alarms» es 30030 en la _D y 30029 en la _I). El usuario la quiere en la wiki y con crédito a quien la publicó.

## Decisión

- Una copia de terceros puede entrar en la carpeta del modelo si lleva SHA-256, revisión y procedencia en el `README.md` de la marca, marcada como «no oficial».
- Es solo referencia histórica. Ningún perfil ni tabla de registros se apoya en ella: manda el PDF oficial más reciente (ADR 0006).
- Las fuentes externas se citan en la sección «Fuentes externas» del `README.md` raíz.

Matiza ADR 0006 sin sustituirla.

## Consecuencias

- `docs/wiki/brands/ingeteam/storage-1-play-tl-m/input_registers_ABH2010IMB08_D.pdf` entra como copia no oficial.
- Un registro que solo aparezca en una copia de terceros sigue sin entrar en un perfil.
