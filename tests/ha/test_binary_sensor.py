"""Entidades binary_sensor: bits del BMS."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from modbus_connection.mock import MockModbusUnit

from tests.ha.common import setup_storage_entry


async def test_bms_bits_are_binary_sensors(
    hass: HomeAssistant, patch_storage_unit: MagicMock, storage_unit: MockModbusUnit
) -> None:
    # 30029 = dirección 28 (alarmas) y 30069 = dirección 68 (estados)
    storage_unit.input.update({28: 0b10, 68: 0b1})
    await setup_storage_entry(hass, components=["battery"])
    assert hass.states.get("binary_sensor.battery_alarm_high_voltage").state == "on"
    assert hass.states.get("binary_sensor.battery_alarm_high_charge_current").state == "off"
    assert hass.states.get("binary_sensor.battery_charge_blocked").state == "on"
    assert len(hass.states.async_entity_ids("binary_sensor")) == 14
