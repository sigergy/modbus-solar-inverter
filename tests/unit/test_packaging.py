"""Manifest coherente con el dominio y con el orden de claves que exige hassfest."""

import json
from pathlib import Path

from custom_components.modbus_solar.const import DOMAIN

PACKAGE = Path(__file__).parents[2] / "custom_components" / "modbus_solar"


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
