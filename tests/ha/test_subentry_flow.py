"""Subentry flow `device`: alta de un equipo con sonda Modbus."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusConnectionError, ModbusExceptionError, ModbusTcpParams
from modbus_connection.mock import MockModbusUnit

from tests.ha.common import DEVICE, brand_entry

USER_INPUT = {
    "name": "Inverter",
    "host": "192.168.1.50",
    "port": 502,
    "unit_id": 1,
    "profile": "ingeteam.oneplay_storage",
}


async def submit(hass: HomeAssistant, entry_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
    result = await hass.config_entries.subentries.async_init((entry_id, "device"), context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)


async def test_add_device(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    result = await submit(hass, entry.entry_id, {**USER_INPUT, "host": "Inverter.LAN"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    subentry = next(iter(entry.subentries.values()))
    assert (subentry.subentry_type, subentry.title, subentry.unique_id) == ("device", "Inverter", "inverter.lan:502:1")
    assert dict(subentry.data) == {
        "host": "Inverter.LAN",
        "port": 502,
        "unit_id": 1,
        "profile": "ingeteam.oneplay_storage",
        "intervals": {"fast": 5, "normal": 60, "slow": 3600},
    }
    _, params, unit_id = temp_unit.call_args.args
    assert (params, unit_id) == (ModbusTcpParams(host="Inverter.LAN", port=502), 1)


async def test_duplicate_device_aborts_before_probing(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = brand_entry(DEVICE)
    entry.add_to_hass(hass)
    result = await submit(hass, entry.entry_id, USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    temp_unit.assert_not_called()


@pytest.mark.parametrize(
    ("break_device", "error"),
    [
        (lambda unit, mock: unit.fail_requests(ModbusConnectionError("refused")), "cannot_connect"),
        (lambda unit, mock: unit.fail_read(0x101D, ModbusExceptionError(2)), "invalid_response"),
        (lambda unit, mock: unit.holding.update({0x101D: 7}), "invalid_response"),
        (lambda unit, mock: setattr(mock, "side_effect", HomeAssistantError("in use")), "endpoint_in_use"),
    ],
)
async def test_probe_errors_show_form_error(
    hass: HomeAssistant,
    temp_unit: MagicMock,
    ingeteam_unit: MockModbusUnit,
    break_device: Any,
    error: str,
) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    break_device(ingeteam_unit, temp_unit)
    result = await submit(hass, entry.entry_id, USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert entry.subentries == {}


async def test_form_recovers_after_error(
    hass: HomeAssistant, temp_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    ingeteam_unit.fail_requests(ModbusConnectionError("refused"))
    result = await submit(hass, entry.entry_id, USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}
    ingeteam_unit.fail_requests(None)
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
