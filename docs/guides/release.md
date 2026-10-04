# Guía: publicar una versión

HACS instala el `modbus_solar.zip` adjunto a cada release (`hacs.json:3-4`).

1. Sube `version` en `custom_components/modbus_solar/manifest.json` (`manifest.json:12`).
2. Merge a `main`.
3. Crea el tag y empújalo:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. `release.yml` se dispara con el tag `v*.*.*` (`.github/workflows/release.yml:3-5`) y:
   - comprueba que `version` del manifest sea igual al tag, y falla si no (`.github/workflows/release.yml:15-18`);
   - empaqueta `custom_components/modbus_solar` en `modbus_solar.zip` (`.github/workflows/release.yml:19-21`);
   - publica la release con el zip y las notas generadas (`.github/workflows/release.yml:22-29`).

El tag debe llevar el prefijo `v` y coincidir exactamente con la versión del manifest: `v0.1.0` para `"version": "0.1.0"`.

Betas: versión PEP 440 con sufijo (`0.1.0b1`, `0.1.0rc1`) y tag igual (`v0.1.0b1`). `release.yml` las publica como prerelease si el tag lleva letras. En HACS solo aparecen con «Mostrar versiones beta» activado en el repositorio.

El workflow `validate` (hassfest y HACS) corre en cada push y pull request (`.github/workflows/validate.yml:3-6`). La licencia es AGPL-3.0 ([ADR 0008](../decisions/0008-license-agpl-3.md)).
