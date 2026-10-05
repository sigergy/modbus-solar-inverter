"""Config flow: alta de un dispositivo (marca, modelo, conexión, componentes, lecturas, nombre) y reconfigure."""

import asyncio
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from dataclasses import replace
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

from custom_components.modbus_solar import CATALOG
from custom_components.modbus_solar.application.catalog import Catalog
from custom_components.modbus_solar.config_flow import ModbusSolarConfigFlow
from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE_DATA, device_entry

CONNECTION = {"host": "192.168.1.50", "advanced": {"port": 502, "unit_id": 1}}


@pytest.fixture(autouse=True)
def no_setup() -> Generator[MagicMock]:
    """Crear o recargar la entry no la arranca: el setup tiene sus propios tests."""
    with patch("custom_components.modbus_solar.async_setup_entry", return_value=True) as mock:
        yield mock


async def start(hass: HomeAssistant, profile: str = "ingeteam_oneplay") -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "user")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"brand": profile.split("_")[0]})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "model")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"profile": profile})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "connection")
    return result


async def connect(hass: HomeAssistant, connection: dict[str, Any] = CONNECTION) -> dict[str, Any]:
    result = await start(hass)
    return await hass.config_entries.flow.async_configure(result["flow_id"], connection)


async def choose(hass: HomeAssistant, result: dict[str, Any], next_step: str) -> dict[str, Any]:
    """Elige una opción de un menú."""
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": next_step})


async def to_name(hass: HomeAssistant, connection: dict[str, Any] = CONNECTION) -> dict[str, Any]:
    """Alta del 1Play, sin componentes opcionales, hasta el paso de nombre."""
    result = await connect(hass, connection)
    assert (result["type"], result["step_id"]) == (FlowResultType.MENU, "readings")
    return await choose(hass, result, "name")


@pytest.fixture
def storage_temp_unit(storage_unit: MockModbusUnit) -> Generator[MagicMock]:
    """Sustituye la unit temporal del config flow por storage_unit."""

    @asynccontextmanager
    async def fake(hass: Any, params: Any, unit_id: int) -> AsyncIterator[MockModbusUnit]:
        yield storage_unit

    with patch("custom_components.modbus_solar.config_flow.async_get_temporary_unit", side_effect=fake) as mock:
        yield mock


async def to_components(hass: HomeAssistant) -> dict[str, Any]:
    """Alta del STORAGE hasta el paso de componentes."""
    result = await start(hass, "ingeteam_oneplay_storage")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "components")
    return result


def field(result: dict[str, Any], name: str) -> Any:
    """Clave del esquema por nombre, con su default y su valor sugerido."""
    return next(k for k in result["data_schema"].schema if str(k) == name)


async def test_brand_then_model(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    selector = result["data_schema"].schema["brand"]
    assert selector.config["options"] == [
        {"value": "ingeteam", "label": "Ingeteam"},
        {"value": "mencke_tegtmeyer", "label": "Ingenieurbüro Mencke & Tegtmeyer"},
    ]
    assert selector.config["mode"] == "list"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"brand": "ingeteam"})
    assert result["step_id"] == "model"
    selector = result["data_schema"].schema["profile"]
    assert [o["value"] for o in selector.config["options"]] == ["ingeteam_oneplay", "ingeteam_oneplay_storage"]
    assert selector.config["translation_key"] == "profile"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"profile": "ingeteam_oneplay_storage"})
    assert result["step_id"] == "connection"


async def test_connection_defaults_come_from_profile(hass: HomeAssistant) -> None:
    result = await start(hass, "ingeteam_oneplay_storage")
    advanced = result["data_schema"].schema["advanced"]
    assert advanced.options == {"collapsed": True}
    assert {str(key): key.default() for key in advanced.schema.schema} == {"port": 502, "unit_id": 1}


async def test_add_inverter(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await connect(hass, {"host": "Inverter.LAN", "advanced": {"port": 502, "unit_id": 1}})
    assert (result["type"], result["step_id"]) == (FlowResultType.MENU, "readings")
    assert result["description_placeholders"] == {
        "host": "Inverter.LAN",
        "readings": "**Inverter**\n- State: Connected to grid\n- Active power: 1,234.5 W",
    }
    result = await choose(hass, result, "name")
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "name")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Roof"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert (entry.title, entry.unique_id, entry.version) == ("Roof", "inverter.lan:502:1", 2)
    assert dict(entry.data) == {
        "host": "Inverter.LAN",
        "port": 502,
        "unit_id": 1,
        "profile": "ingeteam.oneplay",
        "components": [],
        "intervals": {"instant": 5, "fast": 10, "normal": 60, "slow": 3600},
    }
    _, params, unit_id = temp_unit.call_args.args
    assert (params, unit_id) == (ModbusTcpParams(host="Inverter.LAN", port=502), 1)


async def test_name_defaults_to_brand_and_model(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await to_name(hass)
    name = next(iter(result["data_schema"].schema))
    assert (str(name), name.default()) == ("name", "Ingeteam 1Play TL M")


def add_entry(
    hass: HomeAssistant, device_id: int | None = None, host: str = "10.0.0.1", profile: str = "ingeteam.oneplay"
) -> None:
    """Entry v2 ya dada de alta, con Device ID o sin él."""
    data = {**DEVICE_DATA, "host": host, "profile": profile}
    if device_id is not None:
        data["device_id"] = device_id
    device_entry(data, entry_id=f"e_{host}").add_to_hass(hass)


def suggested(result: dict[str, Any], name: str) -> Any:
    """Valor propuesto de un campo del formulario."""
    return field(result, name).description["suggested_value"]


async def submit_name(hass: HomeAssistant, result: dict[str, Any], **values: Any) -> dict[str, Any]:
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "x", **values})


async def test_device_id_defaults_to_lowest_free(hass: HomeAssistant) -> None:
    add_entry(hass, device_id=0)
    add_entry(hass, device_id=2, host="10.0.0.2")
    result = await to_name(hass)
    assert suggested(result, "device_id") == 1
    assert [str(k) for k in result["data_schema"].schema] == ["name", "device_id", "serial_number"]


async def test_device_id_in_use_shows_error(hass: HomeAssistant) -> None:
    add_entry(hass, device_id=0)
    result = await to_name(hass)
    result = await submit_name(hass, result, device_id=0)
    assert result["errors"] == {"device_id": "device_id_in_use"}
    assert result["step_id"] == "name"
    assert result["description_placeholders"]["device_type"] == "inverter"
    assert result["description_placeholders"]["device_id"] == "0"


async def test_device_id_free_across_device_types(hass: HomeAssistant) -> None:
    add_entry(hass, device_id=0, profile="mencke_tegtmeyer.si_rs485")
    result = await to_name(hass)
    assert suggested(result, "device_id") == 0
    result = await submit_name(hass, result, device_id=0)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_entries_without_device_id_do_not_block(hass: HomeAssistant) -> None:
    add_entry(hass)
    result = await to_name(hass)
    assert suggested(result, "device_id") == 0
    result = await submit_name(hass, result, device_id=0)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_invalid_serial_number(hass: HomeAssistant) -> None:
    result = await to_name(hass)
    result = await submit_name(hass, result, device_id=0, serial_number="AB 1")
    assert result["errors"] == {"serial_number": "invalid_serial_number"}
    assert result["step_id"] == "name"


async def test_serial_number_is_stripped_and_saved(hass: HomeAssistant) -> None:
    result = await to_name(hass)
    result = await submit_name(hass, result, device_id=3, serial_number=" AB123 ")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["device_id"] == 3
    assert result["data"]["serial_number"] == "AB123"


async def test_empty_serial_number_is_not_saved(hass: HomeAssistant) -> None:
    result = await to_name(hass)
    result = await submit_name(hass, result, device_id=0, serial_number="  ")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "serial_number" not in result["data"]


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
    assert result["step_id"] == "readings"


async def test_cannot_connect_shows_endpoint(
    hass: HomeAssistant, temp_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    ingeteam_unit.fail_requests(ModbusConnectionError("refused"))
    result = await connect(hass, {"host": "10.0.0.9", "advanced": {"port": 502, "unit_id": 1}})
    assert result["errors"] == {"base": "cannot_connect"}
    assert result["description_placeholders"].items() >= {"host": "10.0.0.9", "port": "502", "timeout": "20"}.items()
    # tras el error aparece el campo «Modelo», con el modelo actual
    assert field(result, "profile").default() == "ingeteam_oneplay"
    options = result["data_schema"].schema["profile"].config["options"]
    assert [o["value"] for o in options] == ["ingeteam_oneplay", "ingeteam_oneplay_storage"]


async def test_model_field_is_not_shown_before_an_error(hass: HomeAssistant) -> None:
    result = await start(hass)
    assert "profile" not in result["data_schema"].schema
    assert result["description_placeholders"].items() >= {"brand": "Ingeteam", "timeout": "20"}.items()


async def test_components_step_then_readings_menu(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass)
    selector = result["data_schema"].schema["components"]
    assert [o["value"] for o in selector.config["options"]] == [
        "pv",
        "battery",
        "grid",
        "internal_meter",
        "critical_loads",
        "load",
        "ev_charger",
    ]
    assert (selector.config["multiple"], selector.config["mode"]) == (True, "list")
    assert selector.config["translation_key"] == "component"
    assert field(result, "components").default() == ["pv", "battery", "grid", "critical_loads", "load"]
    assert result["description_placeholders"] == {"model": "STORAGE 1Play TL M", "main": "Inverter"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": ["battery"]})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["name", "model", "connection"]
    readings = result["description_placeholders"]["readings"]
    assert "**Inverter**" in readings and "**Battery**" in readings
    assert "Solar array" not in readings and "**Grid**" not in readings


async def test_profile_without_components_skips_step(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await connect(hass)
    assert (result["type"], result["step_id"]) == (FlowResultType.MENU, "readings")
    assert result["menu_options"] == ["name", "model", "connection"]


async def test_components_can_be_empty(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": []})
    assert result["type"] is FlowResultType.MENU
    assert "**Battery**" not in result["description_placeholders"]["readings"]


async def test_back_to_model_forgets_components(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": ["battery"]})
    result = await choose(hass, result, "model")
    assert result["step_id"] == "model"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"profile": "ingeteam_oneplay_storage"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert result["step_id"] == "components"
    assert field(result, "components").default() == ["pv", "battery", "grid", "critical_loads", "load"]


async def test_back_to_connection_keeps_values_and_components(
    hass: HomeAssistant, storage_temp_unit: MagicMock
) -> None:
    result = await to_components(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": ["battery"]})
    result = await choose(hass, result, "connection")
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "connection")
    assert field(result, "host").description == {"suggested_value": "192.168.1.50"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert result["step_id"] == "components"
    assert field(result, "components").default() == ["battery"]


async def test_storage_entry_saves_components_in_profile_order(
    hass: HomeAssistant, storage_temp_unit: MagicMock
) -> None:
    result = await to_components(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": ["battery", "pv"]})
    result = await choose(hass, result, "name")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "House"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["components"] == ["pv", "battery"]


async def switch_model_after_error(
    hass: HomeAssistant, ingeteam_unit: MockModbusUnit, temp_unit: MagicMock, advanced: dict[str, int]
) -> Any:
    """Error de conexión con el 1Play y reenvío con el STORAGE, cuyos valores por defecto son 1502 y 3."""
    profiles = [
        replace(p, default_port=1502, default_unit_id=3) if p.id == "ingeteam.oneplay_storage" else p
        for p in CATALOG.for_brand("ingeteam")
    ]
    ingeteam_unit.fail_requests(ModbusConnectionError("refused"))
    with patch.object(ModbusSolarConfigFlow, "catalog", Catalog(profiles)):
        result = await connect(hass)
        assert result["errors"] == {"base": "cannot_connect"}
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "10.0.0.9", "profile": "ingeteam_oneplay_storage", "advanced": advanced}
        )
    params, unit_id = temp_unit.call_args.args[1:]
    return params.port, unit_id


async def test_model_change_after_error_uses_new_defaults_if_advanced_untouched(
    hass: HomeAssistant, temp_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    # 502 y 1 son los valores por defecto del 1Play: no se tocaron
    got = await switch_model_after_error(hass, ingeteam_unit, temp_unit, {"port": 502, "unit_id": 1})
    assert got == (1502, 3)


async def test_model_change_after_error_keeps_touched_advanced(
    hass: HomeAssistant, temp_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    got = await switch_model_after_error(hass, ingeteam_unit, temp_unit, {"port": 1600, "unit_id": 1})
    assert got == (1600, 1)


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
