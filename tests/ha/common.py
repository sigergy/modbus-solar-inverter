"""Datos y utilidades compartidos por los tests con hass."""

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.modbus_solar.const import DOMAIN

DEVICE_ID = "dev1"
DEVICE_DATA: dict[str, Any] = {
    "host": "192.168.1.50",
    "port": 502,
    "unit_id": 1,
    "profile": "ingeteam.oneplay",
    "intervals": {"fast": 5, "normal": 60, "slow": 3600},
}
DEVICE = (DEVICE_ID, "Inverter", DEVICE_DATA)


def brand_entry(*devices: tuple[str, str, dict[str, Any]]) -> MockConfigEntry:
    """Entry de marca Ingeteam con una subentry `device` por tupla (subentry_id, title, data)."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Ingeteam",
        data={"brand": "ingeteam"},
        unique_id="ingeteam",
        subentries_data=[
            {
                "subentry_id": subentry_id,
                "subentry_type": "device",
                "title": title,
                "unique_id": f"{data['host']}:{data['port']}:{data['unit_id']}",
                "data": data,
            }
            for subentry_id, title, data in devices
        ],
    )


def entity_id_of(hass: HomeAssistant, key: str, subentry_id: str = DEVICE_ID) -> str | None:
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{subentry_id}_{key}")


def state_of(hass: HomeAssistant, key: str) -> State | None:
    entity_id = entity_id_of(hass, key)
    return None if entity_id is None else hass.states.get(entity_id)


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    # el primer refresh de cada coordinator va en segundo plano
    await hass.async_block_till_done(wait_background_tasks=True)


async def tick(hass: HomeAssistant, seconds: float) -> None:
    """Avanza el reloj de HA; usar intervalo + 1 para disparar un tier."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done(wait_background_tasks=True)
