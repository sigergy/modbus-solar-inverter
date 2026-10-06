"""Config flow: alta (marca, modelo, conexión, componentes, lecturas, nombre, intervalos) y reconfigure."""

import asyncio
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusConnectionError, ModbusExceptionError, ModbusTcpParams
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_solar import CATALOG
from custom_components.modbus_solar.adapters.inbound.flow import device_label
from custom_components.modbus_solar.application.catalog import Catalog
from custom_components.modbus_solar.config_flow import ModbusSolarConfigFlow
from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE_DATA, STORAGE_DATA, device_entry

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


async def configure(hass: HomeAssistant, result: dict[str, Any], user_input: dict[str, Any]) -> dict[str, Any]:
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def to_metering(hass: HomeAssistant) -> dict[str, Any]:
    """Alta del STORAGE hasta el paso de medición de red."""
    result = await start(hass, "ingeteam_oneplay_storage")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "metering")
    return result


async def to_components(hass: HomeAssistant, metering: str = "grid_loads") -> dict[str, Any]:
    """Alta del STORAGE hasta el paso de componentes."""
    result = await configure(hass, await to_metering(hass), {"metering": metering})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "components")
    return result


ONEPLAY_INTERVALS = {"fast": {"interval": 10}, "normal": {"interval": 60}}
STORAGE_INTERVALS = {
    "instant": {"interval": 5},
    "fast": {"interval": 10},
    "normal": {"interval": 60},
    "slow": {"interval": 3600},
}


async def create(
    hass: HomeAssistant, result: dict[str, Any], intervals: dict[str, Any] = ONEPLAY_INTERVALS
) -> dict[str, Any]:
    """Del paso de nombre al final del alta: envía los intervalos."""
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "intervals")
    return await configure(hass, result, intervals)


async def to_storage_intervals(hass: HomeAssistant) -> dict[str, Any]:
    """Alta del STORAGE con los componentes por defecto hasta el paso de intervalos."""
    result = await to_components(hass)
    result = await configure(hass, result, {"components": ["pv", "battery", "grid", "critical_loads", "load"]})
    result = await choose(hass, result, "name")
    result = await configure(hass, result, {"name": "House", "device_id": 0})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "intervals")
    return result


def interval_defaults(result: dict[str, Any]) -> dict[str, int]:
    """Valor por defecto del campo interval de cada sección del formulario, en el orden del formulario."""
    sections = result["data_schema"].schema
    return {str(tier): next(iter(sections[tier].schema.schema)).default() for tier in sections}


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
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Roof", "device_id": 0})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "intervals")
    result = await create(hass, result)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # el 1Play no tiene modos de medición
    assert "metering" not in result["data"]
    entry = result["result"]
    assert (entry.title, entry.unique_id, entry.version) == ("Roof", "inverter.lan:502:1", 2)
    assert dict(entry.data) == {
        "host": "Inverter.LAN",
        "port": 502,
        "unit_id": 1,
        "profile": "ingeteam.oneplay",
        "components": [],
        "device_id": 0,
        "intervals": {"instant": 5, "fast": 10, "normal": 60, "slow": 3600},
    }
    _, params, unit_id = temp_unit.call_args.args
    assert (params, unit_id) == (ModbusTcpParams(host="Inverter.LAN", port=502), 1)


async def test_name_defaults_to_brand_and_model(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await to_name(hass)
    assert suggested(result, "name") == "Ingeteam 1Play TL M"


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


async def test_device_id_defaults_to_lowest_free(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    add_entry(hass, device_id=0)
    add_entry(hass, device_id=2, host="10.0.0.2")
    result = await to_name(hass)
    assert suggested(result, "device_id") == 1
    assert [str(k) for k in result["data_schema"].schema] == ["name", "device_id", "serial_number"]


async def test_device_id_in_use_shows_error(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    add_entry(hass, device_id=0)
    result = await to_name(hass)
    result = await submit_name(hass, result, device_id=0)
    assert result["errors"] == {"device_id": "device_id_in_use"}
    assert result["step_id"] == "name"
    assert result["description_placeholders"]["device_type"] == "inverter"
    assert result["description_placeholders"]["device_id"] == "0"


async def test_device_id_free_across_device_types(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    add_entry(hass, device_id=0, profile="mencke_tegtmeyer.si_rs485")
    result = await to_name(hass)
    assert suggested(result, "device_id") == 0
    result = await create(hass, await submit_name(hass, result, device_id=0))
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_entries_without_device_id_do_not_block(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    add_entry(hass)
    result = await to_name(hass)
    assert suggested(result, "device_id") == 0
    result = await create(hass, await submit_name(hass, result, device_id=0))
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_invalid_serial_number(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await to_name(hass)
    result = await submit_name(hass, result, device_id=0, serial_number="AB 1")
    assert result["errors"] == {"serial_number": "invalid_serial_number"}
    assert result["step_id"] == "name"


async def test_serial_number_is_stripped_and_saved(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await to_name(hass)
    result = await create(hass, await submit_name(hass, result, device_id=3, serial_number=" AB123 "))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["device_id"] == 3
    assert result["data"]["serial_number"] == "AB123"


async def test_empty_serial_number_is_not_saved(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await to_name(hass)
    result = await create(hass, await submit_name(hass, result, device_id=0, serial_number="  "))
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
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": ["grid", "battery"]})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["name", "model", "connection"]
    readings = result["description_placeholders"]["readings"]
    assert "**Inverter**" in readings and "**Battery**" in readings
    assert "Solar array" not in readings and "**Grid**" in readings


async def test_profile_without_components_skips_step(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await connect(hass)
    assert (result["type"], result["step_id"]) == (FlowResultType.MENU, "readings")
    assert result["menu_options"] == ["name", "model", "connection"]


async def test_back_to_model_forgets_components(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": ["grid", "battery"]})
    result = await choose(hass, result, "model")
    assert result["step_id"] == "model"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"profile": "ingeteam_oneplay_storage"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert result["step_id"] == "metering"
    result = await configure(hass, result, {"metering": "grid_loads"})
    assert result["step_id"] == "components"
    assert field(result, "components").default() == ["pv", "battery", "grid", "critical_loads", "load"]


async def test_back_to_connection_keeps_values_and_components(
    hass: HomeAssistant, storage_temp_unit: MagicMock
) -> None:
    result = await to_components(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"components": ["grid", "battery"]})
    result = await choose(hass, result, "connection")
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "connection")
    assert field(result, "host").description == {"suggested_value": "192.168.1.50"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CONNECTION)
    assert result["step_id"] == "metering"
    result = await configure(hass, result, {"metering": "grid_loads"})
    assert result["step_id"] == "components"
    # en el orden del perfil
    assert field(result, "components").default() == ["battery", "grid"]


async def test_storage_entry_saves_components_in_profile_order(
    hass: HomeAssistant, storage_temp_unit: MagicMock
) -> None:
    result = await to_components(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"components": ["battery", "pv", "grid"]}
    )
    result = await choose(hass, result, "name")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "House", "device_id": 0})
    # con red hay tier instant
    result = await create(hass, result, STORAGE_INTERVALS)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["components"] == ["pv", "battery", "grid"]
    assert result["data"]["metering"] == "grid_loads"


async def test_metering_step_dropdown(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_metering(hass)
    selector = result["data_schema"].schema["metering"]
    assert [o["value"] for o in selector.config["options"]] == ["grid_loads", "critical_loads", "off_grid"]
    assert (selector.config["mode"], selector.config["translation_key"]) == ("dropdown", "metering_mode")
    assert field(result, "metering").default() == "grid_loads"


async def test_metering_mode_forces_its_meter(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    # el vatímetro interno sale marcado aunque el perfil lo tenga desmarcado
    result = await to_components(hass, "critical_loads")
    assert field(result, "components").default() == [
        "pv",
        "battery",
        "grid",
        "internal_meter",
        "critical_loads",
        "load",
    ]
    result = await configure(hass, result, {"components": ["battery"]})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "components")
    assert result["errors"] == {"base": "metering_component_required"}
    assert (
        result["description_placeholders"].items()
        >= {
            "component": "Internal meter",
            "mode": "Loads on Critical Loads",
        }.items()
    )
    # el formulario conserva lo marcado
    assert field(result, "components").default() == ["battery"]


async def test_off_grid_entry_saves_mode(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass, "off_grid")
    result = await configure(hass, result, {"components": ["battery", "internal_meter"]})
    result = await choose(hass, result, "name")
    result = await configure(hass, result, {"name": "Cabin", "device_id": 0})
    # sin Red no hay tier instant
    result = await create(hass, result, {k: v for k, v in STORAGE_INTERVALS.items() if k != "instant"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (result["data"]["metering"], result["data"]["components"]) == ("off_grid", ["battery", "internal_meter"])


async def test_off_grid_intervals_list_generator(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass, "off_grid")
    result = await configure(hass, result, {"components": ["internal_meter"]})
    result = await choose(hass, result, "name")
    result = await configure(hass, result, {"name": "Cabin", "device_id": 0})
    assert "- Generator · Generator power" in result["description_placeholders"]["fast_entities"]
    assert "- Generator · Generator energy" in result["description_placeholders"]["fast_entities"]


async def test_back_to_connection_keeps_metering(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_components(hass, "off_grid")
    result = await configure(hass, result, {"components": ["internal_meter"]})
    result = await choose(hass, result, "connection")
    result = await configure(hass, result, CONNECTION)
    assert result["step_id"] == "metering"
    assert field(result, "metering").default() == "off_grid"


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


async def to_intervals(hass: HomeAssistant, temp_unit: MagicMock) -> dict[str, Any]:
    """Alta del 1Play hasta el paso de intervalos."""
    result = await to_name(hass)
    result = await configure(hass, result, {"name": "Roof", "device_id": 0})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "intervals")
    return result


async def test_intervals_step_shows_only_tiers_with_entities(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await to_intervals(hass, temp_unit)
    # el 1Play no tiene red ni datos lentos: sin sección instant ni slow
    assert [str(k) for k in result["data_schema"].schema] == ["fast", "normal"]
    assert interval_defaults(result) == {"fast": 10, "normal": 60}
    assert result["data_schema"].schema["fast"].options == {"collapsed": True}
    placeholders = result["description_placeholders"]
    assert placeholders.items() >= {"brand": "Ingeteam", "model": "1Play TL M", "fast_min": "2"}.items()
    assert "- Inverter · State" in placeholders["fast_entities"]
    assert "- Inverter · Active power" in placeholders["fast_entities"]


async def test_intervals_step_storage_lists_entities_by_tier(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_storage_intervals(hass)
    assert [str(k) for k in result["data_schema"].schema] == ["instant", "fast", "normal", "slow"]
    assert interval_defaults(result) == {"instant": 5, "fast": 10, "normal": 60, "slow": 3600}
    placeholders = result["description_placeholders"]
    assert placeholders["instant_min"] == "1"
    # spec 4.4: 3 leídas, 2 potencias y 2 energías calculadas; sin controles en este tier
    instant = placeholders["instant_entities"]
    lines = [line for line in instant.splitlines() if line.startswith("- ")]
    assert lines[:3] == ["- Grid · Voltage", "- Grid · Frequency", "- Grid · Power"]
    assert len(lines) == 7
    assert "Grid · Import energy" in instant
    assert "Grid · Grid import power" in instant
    # las entidades desactivadas por defecto llevan la marca
    assert "(disabled)" in placeholders["fast_entities"]


async def test_interval_too_short(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_storage_intervals(hass)
    # instant 1 s cabe; fast 5 s no: el mínimo manda y el presupuesto no se mira
    result = await create(hass, result, {**STORAGE_INTERVALS, "instant": {"interval": 1}, "fast": {"interval": 5}})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "intervals")
    assert result["errors"] == {"fast": "interval_too_short"}
    # el formulario conserva lo escrito
    assert interval_defaults(result)["fast"] == 5


async def test_interval_budget_exceeded(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await to_storage_intervals(hass)
    result = await create(hass, result, {**STORAGE_INTERVALS, "instant": {"interval": 1}})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "intervals")
    assert result["errors"] == {"base": "interval_budget_exceeded"}
    assert float(result["description_placeholders"]["rate"]) > 1
    assert hass.config_entries.async_entries(DOMAIN) == []
    # corregido, se crea la entry
    result = await create(hass, result, STORAGE_INTERVALS)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_unused_tier_interval_is_saved_anyway(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await to_intervals(hass, temp_unit)
    result = await create(hass, result, {"fast": {"interval": 20}, "normal": {"interval": 120}})
    assert result["data"]["intervals"] == {"instant": 5, "fast": 20, "normal": 120, "slow": 3600}


CONNECTION_2 = {"host": "192.168.1.60", "advanced": {"port": 1502, "unit_id": 2}}


async def start_reconfigure(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, Any]:
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure")
    return result


async def reconfigure(
    hass: HomeAssistant, entry: MockConfigEntry, connection: dict[str, Any] = CONNECTION_2
) -> dict[str, Any]:
    result = await start_reconfigure(hass, entry)
    return await configure(hass, result, connection)


def storage_entry(**extra: Any) -> MockConfigEntry:
    return device_entry({**STORAGE_DATA, "components": ["battery"], "device_id": 0, **extra})


async def test_reconfigure_four_steps(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry()
    result = await reconfigure(hass, entry)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_metering")
    result = await configure(hass, result, {"metering": "grid_loads"})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_components")
    # la Red sale marcada: es el vatímetro del modo
    assert field(result, "components").default() == ["battery", "grid"]
    result = await configure(hass, result, {"components": ["grid", "battery"]})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_intervals")
    # lo guardado, completado con los valores por defecto
    assert interval_defaults(result) == {"instant": 5, "fast": 5, "normal": 60, "slow": 3600}
    # nada se guarda hasta el último paso
    assert entry.data["unit_id"] == 1
    result = await configure(hass, result, {**STORAGE_INTERVALS, "normal": {"interval": 120}})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == "192.168.1.60:1502:2"
    assert dict(entry.data) == {
        **STORAGE_DATA,
        "host": "192.168.1.60",
        "port": 1502,
        "unit_id": 2,
        "components": ["battery", "grid"],
        "device_id": 0,
        "metering": "grid_loads",
        "intervals": {"instant": 5, "fast": 10, "normal": 120, "slow": 3600},
    }
    assert entry.title == "Inverter"
    # la sonda usó el endpoint nuevo
    _, params, unit_id = storage_temp_unit.call_args.args
    assert (params, unit_id) == (ModbusTcpParams(host="192.168.1.60", port=1502), 2)


async def test_reconfigure_metering_then_components(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry()
    result = await reconfigure(hass, entry)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_metering")
    # entry sin modo guardado: el primero
    assert field(result, "metering").default() == "grid_loads"
    result = await configure(hass, result, {"metering": "critical_loads"})
    assert result["step_id"] == "reconfigure_components"
    assert field(result, "components").default() == ["battery", "internal_meter"]
    result = await configure(hass, result, {"components": ["battery"]})
    assert result["errors"] == {"base": "metering_component_required"}
    result = await configure(hass, result, {"components": ["battery", "internal_meter"]})
    result = await configure(hass, result, {k: v for k, v in STORAGE_INTERVALS.items() if k != "instant"})
    assert result["reason"] == "reconfigure_successful"
    assert (entry.data["metering"], entry.data["components"]) == ("critical_loads", ["battery", "internal_meter"])


@pytest.mark.parametrize("metering", ["critical_loads", "off_grid"])
async def test_reconfigure_metering_defaults_to_stored(
    hass: HomeAssistant, storage_temp_unit: MagicMock, metering: str
) -> None:
    result = await reconfigure(hass, storage_entry(metering=metering))
    assert field(result, "metering").default() == metering


async def test_reconfigure_profile_without_components_skips_step(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = device_entry()
    result = await reconfigure(hass, entry)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_intervals")
    assert [str(k) for k in result["data_schema"].schema] == ["fast", "normal"]
    result = await configure(hass, result, {"fast": {"interval": 10}, "normal": {"interval": 120}})
    assert result["reason"] == "reconfigure_successful"
    assert dict(entry.data) == {
        **DEVICE_DATA,
        "host": "192.168.1.60",
        "port": 1502,
        "unit_id": 2,
        "components": [],
        "intervals": {"instant": 5, "fast": 10, "normal": 120, "slow": 3600},
    }


async def test_reconfigure_probe_failure_stays(
    hass: HomeAssistant, temp_unit: MagicMock, ingeteam_unit: MockModbusUnit
) -> None:
    ingeteam_unit.fail_requests(ModbusConnectionError("refused"))
    entry = device_entry()
    result = await reconfigure(hass, entry)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure")
    assert result["errors"] == {"base": "cannot_connect"}
    assert result["description_placeholders"].items() >= {"host": "192.168.1.60", "port": "1502"}.items()
    # el formulario conserva lo escrito
    assert field(result, "host").description == {"suggested_value": "192.168.1.60"}
    assert dict(entry.data) == DEVICE_DATA


async def test_reconfigure_rejects_interval_shorter_than_blocks(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = device_entry()
    result = await reconfigure(hass, entry)
    # fast necesita 2 bloques x 1 s; normal 1 bloque x 1 s
    result = await configure(hass, result, {"fast": {"interval": 1}, "normal": {"interval": 1}})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_intervals")
    assert result["errors"] == {"fast": "interval_too_short"}
    assert dict(entry.data) == DEVICE_DATA


async def test_reconfigure_interval_budget_exceeded(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    result = await reconfigure(hass, storage_entry())
    result = await configure(hass, result, {"metering": "grid_loads"})
    # el tier instant solo existe con la red
    result = await configure(hass, result, {"components": ["grid", "battery"]})
    result = await configure(hass, result, {**STORAGE_INTERVALS, "instant": {"interval": 1}})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_intervals")
    assert result["errors"] == {"base": "interval_budget_exceeded"}
    assert float(result["description_placeholders"]["rate"]) > 1


async def test_reconfigure_entry_without_components_defaults_to_all_optional(
    hass: HomeAssistant, storage_temp_unit: MagicMock
) -> None:
    result = await reconfigure(hass, device_entry(STORAGE_DATA))
    assert result["step_id"] == "reconfigure_metering"
    result = await configure(hass, result, {"metering": "grid_loads"})
    assert result["step_id"] == "reconfigure_components"
    assert field(result, "components").default() == [
        "pv",
        "battery",
        "grid",
        "internal_meter",
        "critical_loads",
        "load",
        "ev_charger",
    ]


async def test_reconfigure_aborts_if_endpoint_belongs_to_other_device(
    hass: HomeAssistant, temp_unit: MagicMock
) -> None:
    device_entry().add_to_hass(hass)
    other = device_entry({**DEVICE_DATA, "host": "192.168.1.51"}, entry_id="dev2", title="Inverter 2")
    result = await reconfigure(hass, other, {"host": "192.168.1.50", "advanced": {"port": 502, "unit_id": 1}})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    temp_unit.assert_not_called()


async def test_reconfigure_keeps_own_endpoint(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = device_entry()
    result = await reconfigure(hass, entry, CONNECTION)
    result = await configure(hass, result, ONEPLAY_INTERVALS)
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == "192.168.1.50:502:1"


async def test_reconfigure_prefills_device_id(hass: HomeAssistant) -> None:
    result = await start_reconfigure(hass, device_entry({**DEVICE_DATA, "device_id": 3, "serial_number": "AB1"}))
    key = field(result, "device_id")
    assert isinstance(key, vol.Required)
    assert key.description == {"suggested_value": 3}
    assert field(result, "serial_number").description == {"suggested_value": "AB1"}
    assert field(result, "host").description == {"suggested_value": "192.168.1.50"}
    advanced = result["data_schema"].schema["advanced"]
    assert {str(k): k.default() for k in advanced.schema.schema} == {"port": 502, "unit_id": 1}


async def test_reconfigure_device_id_is_optional_without_stored_id(hass: HomeAssistant) -> None:
    result = await start_reconfigure(hass, device_entry())
    key = field(result, "device_id")
    assert isinstance(key, vol.Optional)
    assert (key.description or {}).get("suggested_value") is None


async def test_reconfigure_device_id_excludes_own_entry(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    add_entry(hass, device_id=1, host="10.0.0.2")
    entry = device_entry({**DEVICE_DATA, "device_id": 0})
    result = await reconfigure(hass, entry, {**CONNECTION, "device_id": 0})
    assert result["step_id"] == "reconfigure_intervals"


async def test_reconfigure_device_id_in_use_does_not_probe(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    add_entry(hass, device_id=1, host="10.0.0.2")
    entry = device_entry({**DEVICE_DATA, "device_id": 0})
    result = await reconfigure(hass, entry, {**CONNECTION, "device_id": 1})
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure")
    assert result["errors"] == {"device_id": "device_id_in_use"}
    temp_unit.assert_not_called()


async def test_reconfigure_same_id_skips_rename(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = device_entry({**DEVICE_DATA, "device_id": 0})
    result = await reconfigure(hass, entry, {**CONNECTION, "device_id": 0})
    assert result["step_id"] == "reconfigure_intervals"
    result = await configure(hass, result, ONEPLAY_INTERVALS)
    # sin cambio de ID no hay formulario de renombrado: el flujo guarda y termina
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert "step_id" not in result


async def test_reconfigure_changed_id_goes_through_rename(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = device_entry({**DEVICE_DATA, "device_id": 0})
    result = await reconfigure(hass, entry, {**CONNECTION, "device_id": 2})
    result = await configure(hass, result, ONEPLAY_INTERVALS)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_rename")
    # nada se guarda hasta confirmar
    assert entry.data["device_id"] == 0
    result = await configure(hass, result, {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["device_id"] == 2


async def test_reconfigure_entry_without_id_can_get_one(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = device_entry()
    result = await reconfigure(hass, entry, {**CONNECTION, "device_id": 4})
    result = await configure(hass, result, ONEPLAY_INTERVALS)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_rename")
    await configure(hass, result, {})
    assert entry.data["device_id"] == 4


async def test_reconfigure_entry_without_id_stays_without(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    entry = device_entry()
    result = await reconfigure(hass, entry, CONNECTION)
    await configure(hass, result, ONEPLAY_INTERVALS)
    assert "device_id" not in entry.data


async def test_reconfigure_invalid_serial_number(hass: HomeAssistant, temp_unit: MagicMock) -> None:
    result = await reconfigure(hass, device_entry(), {**CONNECTION, "serial_number": "AB 1"})
    assert result["errors"] == {"serial_number": "invalid_serial_number"}
    temp_unit.assert_not_called()


async def test_reconfigure_typed_serial_wins_and_empty_serial_is_removed(
    hass: HomeAssistant, temp_unit: MagicMock
) -> None:
    entry = device_entry({**DEVICE_DATA, "serial_number": "OLD1"})
    result = await reconfigure(hass, entry, {**CONNECTION, "serial_number": " NEW2 "})
    await configure(hass, result, ONEPLAY_INTERVALS)
    assert entry.data["serial_number"] == "NEW2"
    # vaciado y sin lectura por Modbus: la clave desaparece de la entry
    result = await entry.start_reconfigure_flow(hass)
    result = await configure(hass, result, CONNECTION)
    await configure(hass, result, ONEPLAY_INTERVALS)
    assert "serial_number" not in entry.data


def seed_entity(
    hass: HomeAssistant, entry: MockConfigEntry, key: str, object_id: str, component: str | None = "battery"
) -> er.RegistryEntry:
    """Entidad sensor de la entry en el registro, colgada del dispositivo del componente (o del principal)."""
    identifier = entry.entry_id if component is None else f"{entry.entry_id}_{component}"
    device = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, identifier)})
    return er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_{key}",
        config_entry=entry,
        device_id=device.id,
        suggested_object_id=object_id,
    )


async def to_rename(hass: HomeAssistant, entry: MockConfigEntry, new_id: int = 2) -> dict[str, Any]:
    """Reconfigure de la entry (ya añadida) hasta el paso de renombrado, cambiando el Device ID a new_id."""
    result = await entry.start_reconfigure_flow(hass)
    result = await configure(hass, result, {**CONNECTION, "device_id": new_id})
    result = await configure(hass, result, {"metering": "grid_loads"})
    result = await configure(hass, result, {"components": ["grid", "battery"]})
    result = await configure(hass, result, STORAGE_INTERVALS)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "reconfigure_rename")
    return result


async def test_reconfigure_rename_renames_generated_ids(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry()
    entry.add_to_hass(hass)
    seeded = seed_entity(hass, entry, "battery_voltage", "battery_0_voltage")
    result = await to_rename(hass, entry)
    result = await configure(hass, result, {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    registry = er.async_get(hass)
    renamed = registry.async_get(seeded.id)
    assert renamed is not None
    assert renamed.entity_id == "sensor.battery_2_voltage"
    assert renamed.unique_id == seeded.unique_id
    assert entry.data["device_id"] == 2


async def test_reconfigure_rename_keeps_custom_ids(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry()
    entry.add_to_hass(hass)
    custom = seed_entity(hass, entry, "battery_current", "my_battery_current")
    result = await to_rename(hass, entry)
    result = await configure(hass, result, {})
    assert result["type"] is FlowResultType.ABORT
    kept = er.async_get(hass).async_get(custom.id)
    assert kept is not None
    assert kept.entity_id == "sensor.my_battery_current"


async def test_reconfigure_rename_skips_collisions(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry()
    entry.add_to_hass(hass)
    clash = seed_entity(hass, entry, "battery_power", "battery_0_power")
    er.async_get(hass).async_get_or_create("sensor", "other", "x1", suggested_object_id="battery_2_power")
    result = await to_rename(hass, entry)
    assert "sensor.battery_0_power" in result["description_placeholders"]["collisions"]
    result = await configure(hass, result, {})
    assert result["type"] is FlowResultType.ABORT
    left = er.async_get(hass).async_get(clash.id)
    assert left is not None
    assert left.entity_id == "sensor.battery_0_power"


async def test_reconfigure_rename_counts_in_placeholders(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    entry = storage_entry()
    entry.add_to_hass(hass)
    seed_entity(hass, entry, "battery_voltage", "battery_0_voltage")
    seed_entity(hass, entry, "battery_soc", "battery_0_soc")
    seed_entity(hass, entry, "battery_current", "my_battery_current")
    seed_entity(hass, entry, "battery_power", "battery_0_power")
    er.async_get(hass).async_get_or_create("sensor", "other", "x1", suggested_object_id="battery_2_power")
    result = await to_rename(hass, entry)
    placeholders = result["description_placeholders"]
    assert (placeholders["old_id"], placeholders["new_id"]) == ("0", "2")
    assert placeholders["renamed_count"] == "2"
    assert placeholders["kept_count"] == "1"
    assert placeholders["collision_count"] == "1"
    assert "`sensor.battery_0_voltage` → `sensor.battery_2_voltage`" in placeholders["examples"]
    assert "`sensor.battery_0_power`" in placeholders["collisions"]


async def test_reconfigure_rename_from_entry_without_id(hass: HomeAssistant, storage_temp_unit: MagicMock) -> None:
    # entry anterior a v2: sin device_id; sus entidades llevan el nombre sin número (spec §4.5)
    data = {**STORAGE_DATA, "components": ["battery"]}
    entry = device_entry(data)
    entry.add_to_hass(hass)
    main = seed_entity(hass, entry, "ac_power", "inverter_power", component=None)
    battery = seed_entity(hass, entry, "battery_voltage", "battery_voltage")
    result = await to_rename(hass, entry)
    assert result["description_placeholders"]["old_id"] == "no ID"
    assert result["description_placeholders"]["renamed_count"] == "2"
    result = await configure(hass, result, {})
    assert result["reason"] == "reconfigure_successful"
    registry = er.async_get(hass)
    renamed_main = registry.async_get(main.id)
    renamed_battery = registry.async_get(battery.id)
    assert renamed_main is not None and renamed_battery is not None
    assert renamed_main.entity_id == "sensor.inverter_2_power"
    assert renamed_battery.entity_id == "sensor.battery_2_voltage"
    assert entry.data["device_id"] == 2


def test_device_label_appends_id_to_plain_name() -> None:
    # prefijo del entity_id: nombre traducido del dispositivo más el ID, sin claves *_numbered
    translations = {f"component.{DOMAIN}.device.grid.name": "Red"}
    assert device_label(translations, "grid", 0) == "Red 0"
    assert device_label(translations, "grid", None) == "Red"
