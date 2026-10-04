"""Config flow: alta de un inversor en tres pasos (modelo, conexión, confirmación) y reconfigure."""

import asyncio
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusConnectionError, ModbusExceptionError, ModbusTcpParams
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE_DATA, device_entry

CONNECTION = {"host": "192.168.1.50", "advanced": {"port": 502, "unit_id": 1}}


@pytest.fixture(autouse=True)
def no_setup() -> Generator[MagicMock]:
    """Crear o recargar la entry no la arranca: el setup tiene sus propios tests."""
    with patch("custom_components.modbus_solar.async_setup_entry", return_value=True) as mock:
        yield mock


async def start(hass: HomeAssistant, profile: str = "ingeteam.oneplay") -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "user")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"profile": profile})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "connection")
    return result


async def connect(hass: HomeAssistant, connection: dict[str, Any] = CONNECTION) -> dict[str, Any]:
    result = await start(hass)
    return await hass.config_entries.flow.async_configure(result["flow_id"], connection)


async def test_model_step_lists_every_profile(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    selector = result["data_schema"].schema["profile"]
    assert selector.config["options"] == [
        {"value": "ingeteam.oneplay", "label": "Ingeteam · 1Play TL M"},
        {"value": "ingeteam.oneplay_storage", "label": "Ingeteam · STORAGE 1Play TL M"},
        {
            "value": "mencke_tegtmeyer.si_rs485",
            "label": (
                "Ingenieurbüro Mencke & Tegtmeyer · "
                "Si-RS485TC-T-MB, Si-RS485TC-2T-MB, Si-RS485TC-2T-v-MB, Si-RS485TC-T-Tm-MB"
            ),
        },
    ]
    assert selector.config["mode"] == "list"


async def test_connection_defaults_come_from_profile(hass: HomeAssistant) -> None:
    result = await start(hass, "ingeteam.oneplay_storage")
    advanced = result["data_schema"].schema["advanced"]
    assert advanced.options == {"collapsed": True}
    assert {str(key): key.default() for key in advanced.schema.schema} == {"port": 502, "unit_id": 1}


async def test_add_inverter(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await connect(hass, {"host": "Inverter.LAN", "advanced": {"port": 502, "unit_id": 1}})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "confirm")
    assert result["description_placeholders"] == {
        "host": "Inverter.LAN",
        "readings": "- Inverter state: Connected to grid\n- Active power: 1234.5 W",
    }
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Roof"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert (entry.title, entry.unique_id, entry.version) == ("Roof", "inverter.lan:502:1", 2)
    assert dict(entry.data) == {
        "host": "Inverter.LAN",
        "port": 502,
        "unit_id": 1,
        "profile": "ingeteam.oneplay",
        "intervals": {"instant": 5, "fast": 10, "normal": 60, "slow": 3600},
    }
    _, params, unit_id = temp_unit.call_args.args
    assert (params, unit_id) == (ModbusTcpParams(host="Inverter.LAN", port=502), 1)


async def test_name_defaults_to_brand_and_model(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await connect(hass)
    name = next(iter(result["data_schema"].schema))
    assert (str(name), name.default()) == ("name", "Ingeteam 1Play TL M")


async def test_duplicate_aborts_before_probing(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    device_entry().add_to_hass(hass)
    result = await connect(hass)
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
    break_device(ingeteam_unit, temp_unit)
    result = await connect(hass)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "connection")
    assert result["errors"] == {"base": error}
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_probe_timeout_is_cannot_connect(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    @asynccontextmanager
    async def silent(hass: Any, params: Any, unit_id: int) -> AsyncIterator[None]:
        # equipo que nunca contesta
        await asyncio.Event().wait()
        yield

    temp_unit.side_effect = silent
    with patch("custom_components.modbus_solar.adapters.inbound.flow.PROBE_TIMEOUT_S", 0.01):
        result = await connect(hass)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_recovers_after_error(
    hass: HomeAssistant, temp_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    ingeteam_unit.fail_requests(ModbusConnectionError("refused"))
    result = await connect(hass)
    assert result["errors"] == {"base": "cannot_connect"}
    ingeteam_unit.fail_requests(None)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert result["step_id"] == "confirm"


RECONFIGURE_INPUT = {"host": "192.168.1.60", "port": 1502, "instant": 5, "fast": 10, "normal": 120, "slow": 3600}


async def reconfigure(hass: HomeAssistant, entry: MockConfigEntry, user_input: dict[str, Any]) -> dict[str, Any]:
    result = await entry.start_reconfigure_flow(hass)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure")
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_reconfigure_updates_host_port_and_intervals(hass: HomeAssistant) -> None:
    entry = device_entry()
    entry.add_to_hass(hass)
    result = await reconfigure(hass, entry, RECONFIGURE_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert (entry.title, entry.unique_id) == ("Inverter", "192.168.1.60:1502:1")
    assert dict(entry.data) == {
        **DEVICE_DATA,
        "host": "192.168.1.60",
        "port": 1502,
        "intervals": {"instant": 5, "fast": 10, "normal": 120, "slow": 3600},
    }


async def test_reconfigure_rejects_interval_shorter_than_blocks(hass: HomeAssistant) -> None:
    entry = device_entry()
    entry.add_to_hass(hass)
    # fast necesita 2 bloques x 1 s; normal 1 bloque x 1 s; slow no tiene entidades
    result = await reconfigure(hass, entry, {**RECONFIGURE_INPUT, "instant": 1, "fast": 1, "normal": 1, "slow": 1})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"fast": "interval_too_short"}
    assert dict(entry.data) == DEVICE_DATA


async def test_reconfigure_aborts_if_endpoint_belongs_to_other_device(hass: HomeAssistant) -> None:
    device_entry().add_to_hass(hass)
    other = device_entry({**DEVICE_DATA, "host": "192.168.1.51"}, entry_id="dev2", title="Inverter 2")
    other.add_to_hass(hass)
    result = await reconfigure(hass, other, {**RECONFIGURE_INPUT, "host": "192.168.1.50", "port": 502})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_keeps_own_endpoint(hass: HomeAssistant) -> None:
    entry = device_entry()
    entry.add_to_hass(hass)
    result = await reconfigure(hass, entry, {**RECONFIGURE_INPUT, "host": "192.168.1.50", "port": 502})
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == "192.168.1.50:502:1"
