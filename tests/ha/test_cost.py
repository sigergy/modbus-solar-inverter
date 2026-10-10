"""Sensores de coste de red del STORAGE: precio fijo, dinámico, caído y restaurado."""

import logging
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import async_fire_time_changed, mock_restore_cache_with_extra_data

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE_ID, STORAGE_DATA, device_entry, entity_id_of, setup_storage_entry, state_of

FIXED = {"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "fixed", "price": 0.05}}
DYNAMIC = {"import": {"mode": "fixed", "price": 0.15}, "export": {"mode": "dynamic", "entity_id": "sensor.price"}}
# la red exporta 300 W (fixture storage_unit)
EXPORTED_6S = 300 * 6 / 3_600_000


async def advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def euros(hass: HomeAssistant, key: str) -> float:
    return float(state_of(hass, key).state)


async def test_cost_sensors_on_the_grid_device(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, None, costs=FIXED)
    for key in ("grid_import_cost", "grid_export_cost"):
        cost = state_of(hass, key)
        attributes = cost.attributes
        assert (attributes["unit_of_measurement"], attributes["device_class"], attributes["state_class"]) == (
            "EUR",
            "monetary",
            "total",
        )
        entity = er.async_get(hass).async_get(entity_id_of(hass, key))
        device = dr.async_get(hass).async_get(entity.device_id)
        assert device.identifiers == {(DOMAIN, f"{DEVICE_ID}_grid")}


async def test_entry_without_costs_has_no_cost_sensors(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, None)
    assert entity_id_of(hass, "grid_import_cost") is None
    assert entity_id_of(hass, "grid_export_cost") is None


async def test_off_grid_has_no_cost_sensors(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, None, metering="off_grid", costs=FIXED)
    assert entity_id_of(hass, "grid_import_cost") is None


async def test_fixed_price(hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock) -> None:
    await setup_storage_entry(hass, None, costs=FIXED)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_export_cost") == pytest.approx(EXPORTED_6S * 0.05)
    assert euros(hass, "grid_import_cost") == 0


async def test_import_cost_on_the_internal_meter(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    # el vatímetro interno (30052) mide 600 W entrando
    storage_unit.input[51] = 600
    await setup_storage_entry(hass, None, metering="critical_loads", costs=FIXED)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_import_cost") == pytest.approx(600 * 6 / 3_600_000 * 0.15)
    entity = er.async_get(hass).async_get(entity_id_of(hass, "grid_import_cost"))
    device = dr.async_get(hass).async_get(entity.device_id)
    assert device.identifiers == {(DOMAIN, f"{DEVICE_ID}_internal_meter")}


async def test_dynamic_price_in_mwh(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    hass.states.async_set("sensor.price", "120", {"unit_of_measurement": "€/MWh"})
    await setup_storage_entry(hass, None, costs=DYNAMIC)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_export_cost") == pytest.approx(EXPORTED_6S * 0.12)


async def test_unavailable_price_keeps_energy_pending(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    patch_storage_unit: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hass.states.async_set("sensor.price", "unavailable", {"unit_of_measurement": "€/kWh"})
    await setup_storage_entry(hass, None, costs=DYNAMIC)
    await advance(hass, freezer, 6)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_export_cost") == 0
    # un aviso por caída, no por muestra
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and "sensor.price" in r.getMessage()]
    assert len(warnings) == 1
    hass.states.async_set("sensor.price", "0.1", {"unit_of_measurement": "€/kWh"})
    await advance(hass, freezer, 6)
    # los 12 s pendientes y los 6 s nuevos, a 0,1
    assert euros(hass, "grid_export_cost") == pytest.approx(3 * EXPORTED_6S * 0.1)


async def test_cost_restored_after_restart(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    # la entidad se crea antes con un entity_id fijo para no depender del nombre del dispositivo
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{DEVICE_ID}_grid_export_cost", suggested_object_id="inverter_grid_export_cost"
    )
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("sensor.inverter_grid_export_cost", "1.5"),
                {"native_value": 1.5, "native_unit_of_measurement": "EUR"},
            )
        ],
    )
    await setup_storage_entry(hass, None, costs=FIXED)
    assert entity_id_of(hass, "grid_export_cost") == "sensor.inverter_grid_export_cost"
    assert euros(hass, "grid_export_cost") == 1.5


async def test_cost_reads_its_source_with_power_and_energy_disabled(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    entry = device_entry({**STORAGE_DATA, "costs": FIXED})
    entry.add_to_hass(hass)
    keys = ("grid_power", "grid_import_power", "grid_export_power", "grid_import_energy", "grid_export_energy")
    for key in keys:
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"{DEVICE_ID}_{key}", config_entry=entry, disabled_by=er.RegistryEntryDisabler.USER
        )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    await advance(hass, freezer, 6)
    assert euros(hass, "grid_export_cost") == pytest.approx(EXPORTED_6S * 0.05)
