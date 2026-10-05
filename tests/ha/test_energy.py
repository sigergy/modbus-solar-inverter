"""Sensores de energía calculada del STORAGE: crecen, se cortan con fallos y se restauran."""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import DEVICE_ID, device_entry, entity_id_of, setup_entry, state_of
from tests.ha.common import STORAGE_DATA as STORAGE


async def advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    # mueve el reloj (t de las muestras) y dispara los tiers vencidos
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def kwh(hass: HomeAssistant, key: str) -> float:
    return float(state_of(hass, key).state)


async def test_core_entities_and_disabled_extra(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    await setup_entry(hass, device_entry(STORAGE))
    assert state_of(hass, "inverter_state").state == "on_grid"
    assert float(state_of(hass, "grid_power").state) == -300
    registry = er.async_get(hass)
    extra = registry.async_get(entity_id_of(hass, "dc_bus_voltage"))
    assert extra.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    energy = state_of(hass, "solar_energy")
    assert (energy.attributes["unit_of_measurement"], energy.attributes["state_class"]) == ("kWh", "total_increasing")
    assert energy.attributes["device_class"] == "energy"


async def test_energy_grows_between_reads(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    await setup_entry(hass, device_entry(STORAGE))
    assert kwh(hass, "solar_energy") == 0
    await advance(hass, freezer, 6)
    # 3000 W durante 6 s
    assert kwh(hass, "solar_energy") == pytest.approx(0.005)
    assert kwh(hass, "grid_export_energy") == pytest.approx(300 * 6 / 3_600_000)
    assert kwh(hass, "grid_import_energy") == 0
    assert kwh(hass, "battery_discharge_energy") == pytest.approx(500 * 6 / 3_600_000)
    assert kwh(hass, "battery_charge_energy") == 0


async def test_read_failure_adds_no_energy(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    await setup_entry(hass, device_entry(STORAGE))
    storage_unit.fail_requests(ModbusConnectionError("no route"))
    await advance(hass, freezer, 6)
    storage_unit.fail_requests(None)
    await advance(hass, freezer, 6)
    # el tramo con el fallo no se integra
    assert kwh(hass, "solar_energy") == 0
    await advance(hass, freezer, 6)
    assert kwh(hass, "solar_energy") == pytest.approx(0.005)


async def test_energy_survives_reload(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    entry = device_entry(STORAGE)
    await setup_entry(hass, entry)
    await advance(hass, freezer, 6)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert kwh(hass, "solar_energy") == pytest.approx(0.005)
    await advance(hass, freezer, 6)
    assert kwh(hass, "solar_energy") == pytest.approx(0.01)


async def test_energy_restored_after_restart(hass: HomeAssistant, patch_storage_unit: MagicMock) -> None:
    # la entidad se crea antes con un entity_id fijo para no depender del nombre del dispositivo
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{DEVICE_ID}_solar_energy", suggested_object_id="inverter_solar_energy"
    )
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("sensor.inverter_solar_energy", "1.5"),
                {"native_value": 1.5, "native_unit_of_measurement": "kWh"},
            )
        ],
    )
    await setup_entry(hass, device_entry(STORAGE))
    assert entity_id_of(hass, "solar_energy") == "sensor.inverter_solar_energy"
    assert kwh(hass, "solar_energy") == 1.5


async def test_energy_counts_with_power_sensor_disabled(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, patch_storage_unit: MagicMock
) -> None:
    entry = device_entry(STORAGE)
    entry.add_to_hass(hass)
    for key in ("pv1_power", "pv2_power"):
        er.async_get(hass).async_get_or_create(
            "sensor",
            DOMAIN,
            f"{DEVICE_ID}_{key}",
            config_entry=entry,
            disabled_by=er.RegistryEntryDisabler.USER,
        )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    await advance(hass, freezer, 6)
    assert kwh(hass, "solar_energy") == pytest.approx(0.005)
