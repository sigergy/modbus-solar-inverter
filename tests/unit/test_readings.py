"""Lecturas de la sonda en el paso de confirmación: nombres y estados traducidos."""

from custom_components.modbus_solar.adapters.inbound.flow import format_readings
from custom_components.modbus_solar.application.poller import TierResult
from custom_components.modbus_solar.profiles.ingeteam.oneplay import ONEPLAY

PREFIX = "component.modbus_solar.entity.sensor"
TRANSLATIONS = {
    f"{PREFIX}.inverter_state.name": "Estado del inversor",
    f"{PREFIX}.inverter_state.state.grid_connected": "Conectado a red",
    f"{PREFIX}.active_power.name": "Potencia activa",
}


def test_names_states_and_units_follow_profile_order() -> None:
    result = TierResult(values={"active_power": 1234.5, "inverter_state": "grid_connected"})
    assert format_readings(ONEPLAY, result, TRANSLATIONS) == (
        "- Estado del inversor: Conectado a red\n- Potencia activa: 1234.5 W"
    )


def test_undecoded_value_shows_dash() -> None:
    result = TierResult(values={"inverter_state": None})
    assert format_readings(ONEPLAY, result, TRANSLATIONS) == "- Estado del inversor: —"


def test_missing_translation_falls_back_to_key() -> None:
    result = TierResult(values={"inverter_state": "grid_connected", "active_power": 5.0})
    assert format_readings(ONEPLAY, result, {}) == "- inverter_state: grid_connected\n- active_power: 5.0 W"
