"""read_tier y min_tier_interval sobre un DeviceGateway falso."""

from dataclasses import replace

import pytest

from custom_components.modbus_solar.application.poller import TierResult, min_tier_interval, read_tier
from custom_components.modbus_solar.domain.errors import DeviceProtocolError, DeviceUnavailable
from custom_components.modbus_solar.domain.types import PollTier
from custom_components.modbus_solar.ports.device import DeviceGateway
from custom_components.modbus_solar.profiles.ingeteam.oneplay_storage import ONEPLAY_STORAGE
from tests.fakes import INGETEAM_WORDS, FakeGateway

ALL_KEYS = {"inverter_state", "active_power", "total_energy"}


async def test_reads_and_decodes_only_the_tier() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    result = await read_tier(PollTier.FAST, gateway, ONEPLAY_STORAGE, ALL_KEYS)
    assert result.values == {"inverter_state": "grid_connected", "active_power": 1234.5}
    assert result.raw == {"inverter_state": (3,), "active_power": (0, 12345)}
    assert result.decode_errors == {}
    assert len(gateway.calls) == 1
    assert {spec.address for spec in gateway.calls[0]} == {0x101D, 0x1037}


async def test_keys_outside_selection_are_not_read() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    result = await read_tier(PollTier.FAST, gateway, ONEPLAY_STORAGE, {"inverter_state"})
    assert result.values == {"inverter_state": "grid_connected"}
    assert [spec.address for spec in gateway.calls[0]] == [0x101D]


async def test_no_keys_does_not_call_gateway() -> None:
    gateway = FakeGateway(INGETEAM_WORDS)
    assert await read_tier(PollTier.SLOW, gateway, ONEPLAY_STORAGE, ALL_KEYS) == TierResult()
    assert await read_tier(PollTier.FAST, gateway, ONEPLAY_STORAGE, set()) == TierResult()
    assert gateway.calls == []


async def test_decode_error_affects_only_its_key() -> None:
    gateway = FakeGateway({**INGETEAM_WORDS, 0x101D: (7,)})
    result = await read_tier(PollTier.FAST, gateway, ONEPLAY_STORAGE, ALL_KEYS)
    assert result.values == {"inverter_state": None, "active_power": 1234.5}
    assert result.raw["inverter_state"] == (7,)
    assert result.decode_errors == {"inverter_state": "inverter_state: value 7 not in enum"}


@pytest.mark.parametrize("error", [DeviceUnavailable("timeout"), DeviceProtocolError("exception 2")])
async def test_gateway_errors_propagate(error: Exception) -> None:
    with pytest.raises(type(error)):
        await read_tier(PollTier.FAST, FakeGateway(INGETEAM_WORDS, error=error), ONEPLAY_STORAGE, ALL_KEYS)


def test_fake_gateway_satisfies_port() -> None:
    gateway: DeviceGateway = FakeGateway(INGETEAM_WORDS)
    assert callable(gateway.read)


@pytest.mark.parametrize(("tier", "expected"), [(PollTier.FAST, 2.0), (PollTier.NORMAL, 1.0), (PollTier.SLOW, 0.0)])
def test_min_tier_interval_for_ingeteam(tier: PollTier, expected: float) -> None:
    # fast: 0x101D y 0x1037 no son contiguos -> 2 bloques x 1.0 s
    assert min_tier_interval(ONEPLAY_STORAGE, tier) == expected


def test_min_tier_interval_uses_profile_max_gap() -> None:
    # 0x101D y 0x1037 quedan a 25 registros: con max_gap=25 se leen en un bloque
    assert min_tier_interval(replace(ONEPLAY_STORAGE, max_gap=25), PollTier.FAST) == 1.0
