"""Manifest coherente con el dominio y con el orden de claves que exige hassfest."""

import json
import struct
from pathlib import Path

from custom_components.modbus_solar.const import DOMAIN

PACKAGE = Path(__file__).parents[2] / "custom_components" / "modbus_solar"
ROOT = PACKAGE.parents[1]


def load_manifest() -> dict:
    return json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))


def test_manifest_domain_matches_package() -> None:
    manifest = load_manifest()
    assert manifest["domain"] == DOMAIN == PACKAGE.name


def test_manifest_key_order_for_hassfest() -> None:
    # hassfest: domain, name y el resto en orden alfabético
    keys = list(load_manifest())
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def test_manifest_uses_core_modbus() -> None:
    manifest = load_manifest()
    assert manifest["dependencies"] == ["modbus"]
    assert manifest["requirements"] == []


def test_manifest_one_device_per_entry() -> None:
    assert load_manifest()["integration_type"] == "device"


def test_hacs_json() -> None:
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs == {
        "name": "Modbus Solar",
        "zip_release": True,
        "filename": "modbus_solar.zip",
        "homeassistant": "2026.9.0",
    }


def test_brand_icon_is_256_png() -> None:
    data = (PACKAGE / "brand" / "icon.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    # cabecera IHDR: ancho y alto en los bytes 16-24
    assert struct.unpack(">II", data[16:24]) == (256, 256)
