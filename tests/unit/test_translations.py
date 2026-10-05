"""Traducciones: en.json igual a strings.json; es.json con las mismas claves; nada sin traducir."""

import json
import re
from pathlib import Path
from typing import Any

from custom_components.modbus_solar.adapters.inbound.flow import profile_option
from custom_components.modbus_solar.domain.types import Component, PollTier
from custom_components.modbus_solar.profiles import ALL_PROFILES

# hassfest translation_key_validator
TRANSLATION_KEY = re.compile(r"^(?!.+[_-]{2})(?![_-])[a-z0-9-_]+(?<![_-])$")
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
    entities = load("strings.json")["entity"]
    options: dict[str, set[str]] = {}
    for profile in ALL_PROFILES:
        for spec in profile.entities:
            # el nombre está en la sección de su plataforma (sensor, binary_sensor)
            assert "name" in entities[spec.platform.value][spec.key], spec.key
            if spec.enum is not None:
                options.setdefault(spec.key, set()).update(spec.enum.values())
        for energy in profile.energies:
            assert "name" in entities["sensor"][energy.key], energy.key
    # la clave es translation_key en todos los perfiles: state lleva la unión de sus opciones
    for key, values in options.items():
        assert set(entities["sensor"][key]["state"]) == values, key


def test_entity_short_names() -> None:
    # spec §5.4: la entidad no repite su dispositivo
    expected = {
        "strings.json": {
            "battery_soc": "State of charge",
            "grid_power": "Power",
            "solar_energy": "PV energy",
            "power_reduction_ratio": "Power reduction ratio",
            "bms_alarm_high_voltage": "Alarm: high voltage",
        },
        "translations/es.json": {
            "battery_soc": "Estado de carga",
            "grid_power": "Potencia",
            "solar_energy": "Energía FV",
            "power_reduction_ratio": "Ratio de reducción de potencia",
            "bms_alarm_high_voltage": "Alarma: tensión alta",
        },
    }
    for name, names in expected.items():
        entities = load(name)["entity"]
        got = {k: entities["binary_sensor" if k.startswith("bms_") else "sensor"][k]["name"] for k in names}
        assert got == names, name


def test_flow_steps_errors_and_aborts_are_translated() -> None:
    strings = load("strings.json")
    config = strings["config"]
    assert set(config["step"]) == {"user", "model", "connection", "components", "readings", "name", "reconfigure"}
    assert set(config["step"]["connection"]["sections"]) == {"advanced"}
    assert set(config["error"]) == {
        "cannot_connect",
        "endpoint_in_use",
        "invalid_response",
        "interval_too_short",
        "device_id_in_use",
        "invalid_serial_number",
    }
    assert set(config["abort"]) == {"already_configured", "reconfigure_successful"}
    assert "config_subentries" not in strings


def test_controls_and_write_error_are_translated() -> None:
    strings = load("strings.json")
    for profile in ALL_PROFILES:
        for control in profile.controls:
            assert "name" in strings["entity"]["number"][control.key], control.key
            assert "name" in strings["entity"]["switch"][control.switch_key], control.switch_key
    assert "{error}" in strings["exceptions"]["write_failed"]["message"]


def test_flow_texts_do_not_say_inverter() -> None:
    # el alta sirve a cualquier equipo (inversor, sensor…): sin «inverter» ni «inversor»
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        for step in ("user", "connection", "name"):
            step_texts = load(name)["config"]["step"][step]
            for field in ("title", "description"):
                text = step_texts.get(field, "").lower()
                assert "inverter" not in text and "inversor" not in text, f"{name} {step}.{field}"


def test_irradiance_sensor_entities_are_named() -> None:
    expected = {
        "strings.json": {
            "irradiance": "Irradiance",
            "wind_speed": "Wind speed",
            "cell_temperature": "Cell temperature",
            "external_temperature": "External temperature",
        },
        "translations/es.json": {
            "irradiance": "Irradiancia",
            "wind_speed": "Velocidad del viento",
            "cell_temperature": "Temperatura de la célula",
            "external_temperature": "Temperatura externa",
        },
    }
    for name, names in expected.items():
        sensors = load(name)["entity"]["sensor"]
        assert {key: sensors[key]["name"] for key in names} == names, name


def test_interval_fields_cover_every_tier() -> None:
    for name in ("strings.json", "translations/es.json"):
        data = load(name)["config"]["step"]["reconfigure"]["data"]
        for tier in PollTier:
            assert tier.value in data, (name, tier)


def test_every_device_has_numbered_variant() -> None:
    keys = {p.device_type for p in ALL_PROFILES} | {c.value for c in Component if c is not Component.MAIN}
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        devices = load(name)["device"]
        for key in keys:
            assert devices[key]["name"], (name, key)
            assert "{device_id}" in devices[f"{key}_numbered"]["name"], (name, key)


def test_every_profile_has_model_label() -> None:
    for profile in ALL_PROFILES:
        key = profile_option(profile.id)
        assert TRANSLATION_KEY.match(key), key
        assert key in load("strings.json")["selector"]["profile"]["options"], key
        assert key in load("translations/es.json")["selector"]["profile"]["options"], key


def test_every_optional_component_has_label() -> None:
    components = {c.component.value for p in ALL_PROFILES for c in p.components}
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        assert components <= set(load(name)["selector"]["component"]["options"]), name


def test_readings_menu_and_connection_errors_have_placeholders() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        config = load(name)["config"]
        assert set(config["step"]["readings"]["menu_options"]) == {"name", "model", "connection"}, name
        assert "{host}" in config["step"]["readings"]["description"], name
        assert "{readings}" in config["step"]["readings"]["description"], name
        for error in ("cannot_connect", "invalid_response"):
            assert "{host}:{port}" in config["error"][error], (name, error)
        assert "{timeout}" in config["error"]["cannot_connect"], name
