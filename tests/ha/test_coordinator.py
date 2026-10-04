"""TierCoordinator, enabled_keys y build_runtime con hass."""

import logging
from dataclasses import replace
from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.modbus_solar.adapters.inbound.coordinator import TierCoordinator
from custom_components.modbus_solar.adapters.inbound.runtime import build_runtime, enabled_keys
from custom_components.modbus_solar.const import DOMAIN
from custom_components.modbus_solar.domain.control import GatedState
from custom_components.modbus_solar.domain.errors import DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.domain.types import PollTier
from custom_components.modbus_solar.profiles.ingeteam.oneplay import ONEPLAY
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE
from tests.fakes import INGETEAM_WORDS, FakeGateway, FakeWriter
from tests.ha.common import DEVICE_ID, device_entry

ALL_KEYS = frozenset({"inverter_state", "active_power", "total_energy"})


def make_coordinator(hass: HomeAssistant, gateway: FakeGateway) -> TierCoordinator:
    entry = device_entry()
    entry.add_to_hass(hass)
    return TierCoordinator(
        hass,
        entry,
        name="Inverter fast",
        tier=PollTier.FAST,
        interval_s=5,
        gateway=gateway,
        profile=ONEPLAY,
        keys=ALL_KEYS,
    )


async def test_refresh_stores_tier_result(hass: HomeAssistant) -> None:
    coordinator = make_coordinator(hass, FakeGateway(INGETEAM_WORDS))
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.data.values == {"inverter_state": "grid_connected", "active_power": 1234.5}
    assert coordinator.update_interval == timedelta(seconds=5)
    assert (coordinator.tier, coordinator.keys) == (PollTier.FAST, ALL_KEYS)
    assert (coordinator.last_error, coordinator.last_error_at) == (None, None)


@pytest.mark.parametrize("error", [DeviceUnavailable("timeout"), DeviceProtocolError("exception 2")])
async def test_domain_errors_fail_the_update(hass: HomeAssistant, error: Exception) -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    coordinator = make_coordinator(hass, gateway)
    await coordinator.async_refresh()
    gateway.error = error
    await coordinator.async_refresh()
    assert not coordinator.last_update_success
    assert coordinator.last_error == f"{type(error).__name__}: {error}"
    assert coordinator.last_error_at is not None
    # data conserva la última lectura correcta (para diagnostics)
    assert coordinator.data.values["active_power"] == 1234.5


async def test_decode_warning_once_per_key_until_recovery(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    gateway = FakeGateway({**INGETEAM_WORDS, 0x101D: (7,)})
    coordinator = make_coordinator(hass, gateway)
    await coordinator.async_refresh()
    await coordinator.async_refresh()
    assert caplog.text.count("value 7 not in enum") == 1
    assert coordinator.last_update_success
    gateway.words[0x101D] = (3,)
    await coordinator.async_refresh()
    gateway.words[0x101D] = (7,)
    await coordinator.async_refresh()
    assert caplog.text.count("value 7 not in enum") == 2


async def test_enabled_keys_follow_entity_registry(hass: HomeAssistant) -> None:
    entry = device_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    # sin entidades registradas: manda enabled_default del perfil
    assert enabled_keys(registry, DEVICE_ID, ONEPLAY) == ALL_KEYS
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DEVICE_ID}_active_power",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    assert enabled_keys(registry, DEVICE_ID, ONEPLAY) == ALL_KEYS - {"active_power"}


async def test_enabled_keys_respect_enabled_default(hass: HomeAssistant) -> None:
    state, *rest = ONEPLAY.entities
    profile = replace(ONEPLAY, entities=(replace(state, enabled_default=False), *rest))
    assert enabled_keys(er.async_get(hass), DEVICE_ID, profile) == ALL_KEYS - {"inverter_state"}


async def test_build_runtime_one_coordinator_per_tier_with_entities(hass: HomeAssistant) -> None:
    entry = device_entry()
    entry.add_to_hass(hass)
    gateway = FakeGateway(INGETEAM_WORDS)
    writer = FakeWriter()
    runtime = build_runtime(hass, entry, ONEPLAY, gateway, writer, ALL_KEYS)
    assert (runtime.entry_id, runtime.title, runtime.profile.id) == (DEVICE_ID, "Inverter", ONEPLAY.id)
    assert runtime.intervals == {"instant": 5, "fast": 5, "normal": 60, "slow": 3600}
    assert runtime.gateway is gateway
    assert runtime.writer is writer
    assert runtime.control_states == {}
    # el perfil Ingeteam no tiene entidades slow
    assert set(runtime.coordinators) == {PollTier.FAST, PollTier.NORMAL}
    assert runtime.coordinators[PollTier.NORMAL].update_interval == timedelta(seconds=60)
    assert runtime.coordinators[PollTier.FAST].keys == ALL_KEYS
    assert not runtime.coordinators[PollTier.FAST].always_update


async def test_energy_sources_are_read_with_power_sensor_disabled(hass: HomeAssistant) -> None:
    entry = device_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DEVICE_ID}_pv1_power",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    # solar_energy sigue activa: necesita pv1_power aunque su sensor esté deshabilitado
    assert "pv1_power" in enabled_keys(registry, DEVICE_ID, ONEPLAY_STORAGE)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{DEVICE_ID}_solar_energy",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    assert "pv1_power" not in enabled_keys(registry, DEVICE_ID, ONEPLAY_STORAGE)


async def test_tiers_with_energy_sources_always_update(hass: HomeAssistant) -> None:
    entry = device_entry()
    entry.add_to_hass(hass)
    runtime = build_runtime(hass, entry, ONEPLAY_STORAGE, FakeGateway({}), FakeWriter(), set())
    assert {tier: c.always_update for tier, c in runtime.coordinators.items()} == {
        PollTier.FAST: True,
        PollTier.NORMAL: False,
        PollTier.SLOW: False,
    }
    # un estado por control, con el límite por defecto del perfil
    assert runtime.control_states == {"export_limit": GatedState(limit=6000)}
