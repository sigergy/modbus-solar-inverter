"""Traducciones: en.json igual a strings.json; es.json con las mismas claves; nada sin traducir."""

import json
import re
from pathlib import Path
from typing import Any

from custom_components.modbus_solar.adapters.inbound.flow import profile_option
from custom_components.modbus_solar.domain.types import Component, PollTier
from custom_components.modbus_solar.profiles import ALL_PROFILES
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import EXPORT_CONTROL

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
        for mode in profile.metering_modes:
            for flow in mode.flows:
                assert "name" in entities["sensor"][flow.power_key], flow.power_key
                assert "name" in entities["sensor"][flow.energy_key], flow.energy_key
                if flow.cost_key is not None:
                    assert "name" in entities["sensor"][flow.cost_key], flow.cost_key
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


def test_metering_entity_names() -> None:
    expected = {
        "strings.json": {
            "grid_import_power": "Grid import power",
            "grid_export_power": "Grid export power",
            "generator_power": "Generator power",
            "generator_energy": "Generator energy",
        },
        "translations/es.json": {
            "grid_import_power": "Potencia de red",
            "grid_export_power": "Potencia a la red",
            "generator_power": "Potencia del generador",
            "generator_energy": "Energía del generador",
        },
    }
    for name, names in expected.items():
        sensors = load(name)["entity"]["sensor"]
        assert {key: sensors[key]["name"] for key in names} == names, name


def test_cost_entity_names() -> None:
    expected = {
        "strings.json": {"grid_import_cost": "Grid import cost", "grid_export_cost": "Grid export cost"},
        "translations/es.json": {
            "grid_import_cost": "Coste de la energía importada",
            "grid_export_cost": "Coste de la energía exportada",
        },
    }
    for name, names in expected.items():
        sensors = load(name)["entity"]["sensor"]
        assert {key: sensors[key]["name"] for key in names} == names, name


def test_flow_steps_errors_and_aborts_are_translated() -> None:
    strings = load("strings.json")
    config = strings["config"]
    assert set(config["step"]) == {
        "user",
        "model",
        "connection",
        "metering",
        "costs",
        "cost_prices",
        "components",
        "readings",
        "name",
        "intervals",
        "reconfigure",
        "reconfigure_metering",
        "reconfigure_costs",
        "reconfigure_cost_prices",
        "reconfigure_components",
        "reconfigure_intervals",
        "reconfigure_rename",
    }
    assert set(config["step"]["connection"]["sections"]) == {"advanced"}
    assert set(config["error"]) == {
        "cannot_connect",
        "endpoint_in_use",
        "invalid_response",
        "interval_too_short",
        "interval_budget_exceeded",
        "device_id_in_use",
        "invalid_serial_number",
        "metering_component_required",
        "price_unit_invalid",
    }
    assert set(config["abort"]) == {"already_configured", "reconfigure_successful"}
    assert "config_subentries" not in strings


def test_cost_steps_and_modes_are_translated() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        data = load(name)
        steps = data["config"]["step"]
        assert set(steps["costs"]["data"]) == {"enabled", "import_mode", "export_mode"}, name
        assert set(steps["cost_prices"]["data"]) == {"import_price", "export_price", "import_entity", "export_entity"}
        assert set(data["selector"]["cost_mode"]["options"]) == {"fixed", "dynamic"}, name
        assert data["config"]["error"]["price_unit_invalid"], name
        assert steps["reconfigure_costs"]["data"] == steps["costs"]["data"], name
        assert steps["reconfigure_cost_prices"]["data"] == steps["cost_prices"]["data"], name
    assert load("translations/es.json")["selector"]["cost_mode"]["options"] == {
        "fixed": "Precio fijo",
        "dynamic": "Precio dinámico (entidad)",
    }


def test_metering_step_and_modes_are_translated() -> None:
    modes = {m.key for p in ALL_PROFILES for m in p.metering_modes}
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        data = load(name)
        assert set(data["selector"]["metering_mode"]["options"]) == modes, name
        step = data["config"]["step"]["metering"]
        assert step["title"] and step["data"]["metering"] and "{model}" in step["description"], name
        error = data["config"]["error"]["metering_component_required"]
        assert "{component}" in error and "{mode}" in error, name
    labels = {
        "strings.json": ["Loads on Grid", "Loads on Critical Loads", "Off-grid"],
        "translations/es.json": ["Consumos en Grid", "Consumos en Cargas Críticas", "Aislada"],
    }
    for name, expected in labels.items():
        assert list(load(name)["selector"]["metering_mode"]["options"].values()) == expected, name


def test_controls_and_write_error_are_translated() -> None:
    strings = load("strings.json")
    # los controles desactivados en su perfil también conservan su traducción
    controls = {EXPORT_CONTROL, *(control for profile in ALL_PROFILES for control in profile.controls)}
    for control in controls:
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


def test_interval_sections_cover_every_tier() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        steps = load(name)["config"]["step"]
        for step in ("intervals", "reconfigure_intervals"):
            sections = steps[step]["sections"]
            assert set(sections) == {tier.value for tier in PollTier}, (name, step)
            for tier in PollTier:
                section = sections[tier.value]
                assert section["name"], (name, step, tier)
                assert section["data"]["interval"], (name, step, tier)
                # los placeholders de cada tier los rellena el flujo (spec 4.3)
                text = section["data_description"]["interval"]
                assert f"{{{tier.value}_min}}" in text and f"{{{tier.value}_entities}}" in text, (name, step, tier)


def test_reconfigure_connection_step_texts() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        step = load(name)["config"]["step"]["reconfigure"]
        assert set(step["data"]) == {"host", "device_id", "serial_number"}, name
        assert set(step["sections"]) == {"advanced"}, name
        assert step["submit"], name
        assert "{brand}" in step["description"] and "{model}" in step["description"], name
        assert "{serial_help}" in step["data_description"]["serial_number"], name


def test_entity_list_markers_and_budget_error_are_translated() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        data = load(name)
        assert set(data["selector"]["entity_list"]["options"]) == {"disabled", "calculated"}, name
        assert "reconfigure" in data["selector"]["serial_help"]["options"], name
        assert "{rate}" in data["config"]["error"]["interval_budget_exceeded"], name


def test_device_names_have_no_device_id() -> None:
    # el ID va en el entity_id, no en el nombre del dispositivo
    keys = {p.device_type for p in ALL_PROFILES} | {c.value for c in Component if c is not Component.MAIN}
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        devices = load(name)["device"]
        assert set(devices) == keys, name
        for key in keys:
            assert devices[key]["name"], (name, key)
            assert "{device_id}" not in devices[key]["name"], (name, key)


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


def test_reconfigure_rename_step_texts() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        step = load(name)["config"]["step"]["reconfigure_rename"]
        assert step["title"] and step["submit"], name
        for placeholder in (
            "old_id",
            "new_id",
            "renamed_count",
            "examples",
            "kept_count",
            "collision_count",
            "collisions",
        ):
            assert f"{{{placeholder}}}" in step["description"], (name, placeholder)
    # texto de «old_id» cuando la entry no tiene ID
    for name, text in (
        ("strings.json", "no ID"),
        ("translations/en.json", "no ID"),
        ("translations/es.json", "sin ID"),
    ):
        assert load(name)["selector"]["rename_old_id"]["options"]["none"] == text, name


def test_reconfigure_metering_step_texts() -> None:
    for name in ("strings.json", "translations/en.json", "translations/es.json"):
        step = load(name)["config"]["step"]["reconfigure_metering"]
        assert step["title"] and step["data"]["metering"] and step["submit"], name
        assert "{model}" in step["description"], name
