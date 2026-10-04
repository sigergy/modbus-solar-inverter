"""Traducciones: en.json igual a strings.json; es.json con las mismas claves; nada sin traducir."""

import json
from pathlib import Path
from typing import Any

from custom_components.modbus_solar.profiles import ALL_PROFILES

ROOT = Path(__file__).parents[2] / "custom_components" / "modbus_solar"


def load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def leaf_paths(tree: dict[str, Any], prefix: str = "") -> set[str]:
    paths: set[str] = set()
    for key, value in tree.items():
        path = f"{prefix}{key}"
        paths |= leaf_paths(value, f"{path}.") if isinstance(value, dict) else {path}
    return paths


def test_en_is_literal_copy_of_strings() -> None:
    assert load("translations/en.json") == load("strings.json")


def test_es_has_the_same_keys() -> None:
    assert leaf_paths(load("translations/es.json")) == leaf_paths(load("strings.json"))


def test_every_entity_and_enum_state_is_translated() -> None:
    sensors = load("strings.json")["entity"]["sensor"]
    options: dict[str, set[str]] = {}
    for profile in ALL_PROFILES:
        for spec in profile.entities:
            assert "name" in sensors[spec.key], spec.key
            if spec.enum is not None:
                options.setdefault(spec.key, set()).update(spec.enum.values())
        for energy in profile.energies:
            assert "name" in sensors[energy.key], energy.key
    # la clave es translation_key en todos los perfiles: state lleva la unión de sus opciones
    for key, values in options.items():
        assert set(sensors[key]["state"]) == values, key


def test_flow_steps_errors_and_aborts_are_translated() -> None:
    strings = load("strings.json")
    config = strings["config"]
    assert set(config["step"]) == {"user", "connection", "confirm", "reconfigure"}
    assert set(config["step"]["connection"]["sections"]) == {"advanced"}
    assert set(config["error"]) == {"cannot_connect", "endpoint_in_use", "invalid_response", "interval_too_short"}
    assert set(config["abort"]) == {"already_configured", "reconfigure_successful"}
    assert "config_subentries" not in strings
