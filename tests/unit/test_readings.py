"""Lecturas de la sonda en el paso de lecturas: grupos por componente, nombres y estados traducidos."""

from custom_components.modbus_solar.adapters.inbound.flow import format_readings
from custom_components.modbus_solar.application.poller import TierResult
from custom_components.modbus_solar.application.probe import ProbeResult
from custom_components.modbus_solar.application.selection import select
from custom_components.modbus_solar.domain.types import Component
from custom_components.modbus_solar.profiles.ingeteam.oneplay import ONEPLAY
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE

PREFIX = "component.modbus_solar.entity.sensor"
DEVICE = "component.modbus_solar.device"
TRANSLATIONS = {
    f"{PREFIX}.inverter_state.name": "Estado",
    f"{PREFIX}.inverter_state.state.grid_connected": "Conectado a red",
    f"{PREFIX}.active_power.name": "Potencia activa",
    f"{PREFIX}.pv1_power.name": "Potencia FV1",
    f"{PREFIX}.battery_soc.name": "Estado de carga",
    f"{DEVICE}.inverter.name": "Inversor",
    f"{DEVICE}.pv.name": "Campo solar",
    f"{DEVICE}.battery.name": "Batería",
}


def probed(values: dict[str, object]) -> ProbeResult:
    return ProbeResult(readings=TierResult(values=values), serial=None)


def test_group_title_is_device_name_and_values_follow_profile_order() -> None:
    result = probed({"active_power": 1234.5, "inverter_state": "grid_connected"})
    assert format_readings(ONEPLAY, select(ONEPLAY, []), result, TRANSLATIONS, "en") == (
        "**Inversor**\n- Estado: Conectado a red\n- Potencia activa: 1,234.5 W"
    )


def test_thousands_separator_follows_language() -> None:
    selection = select(ONEPLAY, [])
    result = probed({"active_power": 1234.5})
    assert format_readings(ONEPLAY, selection, result, {}, "en").endswith("active_power: 1,234.5 W")
    assert format_readings(ONEPLAY, selection, result, {}, "es").endswith("active_power: 1.234,5 W")
    negative = probed({"active_power": -1234})
    assert format_readings(ONEPLAY, selection, negative, {}, "en").endswith("-1,234 W")
    assert format_readings(ONEPLAY, selection, negative, {}, "es").endswith("-1.234 W")


def test_groups_follow_profile_order_not_selection_order() -> None:
    selection = select(ONEPLAY_STORAGE, [Component.BATTERY, Component.PV])
    result = probed({"battery_soc": 85, "pv1_power": 820.0, "inverter_state": "on_grid"})
    text = format_readings(ONEPLAY_STORAGE, selection, result, TRANSLATIONS, "es")
    titles = [line for line in text.splitlines() if line.startswith("**")]
    assert titles == ["**Inversor**", "**Campo solar**", "**Batería**"]


def test_component_not_selected_does_not_appear() -> None:
    selection = select(ONEPLAY_STORAGE, [Component.BATTERY])
    result = probed({"battery_soc": 85, "pv1_power": 820.0})
    text = format_readings(ONEPLAY_STORAGE, selection, result, TRANSLATIONS, "es")
    assert "Campo solar" not in text and "Potencia FV1" not in text
    assert "**Batería**\n- Estado de carga: 85 %" in text


def test_binary_sensors_do_not_appear_and_empty_group_is_dropped() -> None:
    selection = select(ONEPLAY_STORAGE, [Component.BATTERY])
    result = probed({"bms_alarm_high_voltage": False})
    assert format_readings(ONEPLAY_STORAGE, selection, result, TRANSLATIONS, "es") == ""


def test_undecoded_value_shows_dash() -> None:
    result = probed({"inverter_state": None})
    assert format_readings(ONEPLAY, select(ONEPLAY, []), result, TRANSLATIONS, "es") == "**Inversor**\n- Estado: —"


def test_missing_translation_falls_back_to_key() -> None:
    result = probed({"inverter_state": "grid_connected", "active_power": 5.0})
    assert format_readings(ONEPLAY, select(ONEPLAY, []), result, {}, "es") == (
        "**inverter**\n- inverter_state: grid_connected\n- active_power: 5.0 W"
    )
