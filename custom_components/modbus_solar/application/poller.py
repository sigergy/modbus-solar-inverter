"""Lectura de un tier: una llamada al gateway y decodificación por entidad."""

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

from ..domain.blocks import plan_blocks
from ..domain.decode import decode
from ..domain.errors import DecodeError
from ..domain.profile import DeviceProfile
from ..domain.types import PollTier
from ..ports.device import DeviceGateway


@dataclass(frozen=True)
class TierResult:
    values: dict[str, int | float | str | None] = field(default_factory=dict)
    raw: dict[str, tuple[int, ...]] = field(default_factory=dict)
    decode_errors: dict[str, str] = field(default_factory=dict)


async def read_tier(
    tier: PollTier,
    gateway: DeviceGateway,
    profile: DeviceProfile,
    keys: Collection[str],
) -> TierResult:
    # keys = entidades habilitadas: no se leen registros de entidades deshabilitadas
    specs = [e for e in profile.entities if e.poll is tier and e.key in keys]
    if not specs:
        return TierResult()
    words = await gateway.read([e.register for e in specs])
    values: dict[str, int | float | str | None] = {}
    raw: dict[str, tuple[int, ...]] = {}
    errors: dict[str, str] = {}
    for spec in specs:
        raw[spec.key] = tuple(words[spec.register])
        try:
            values[spec.key] = decode(spec, raw[spec.key])
        except DecodeError as err:
            # un valor inválido deja la entidad en unknown sin abortar el tier
            values[spec.key] = None
            errors[spec.key] = str(err)
    return TierResult(values=values, raw=raw, decode_errors=errors)


def min_tier_interval(profile: DeviceProfile, tier: PollTier) -> float:
    """Segundos mínimos para leer el tier entero respetando el espaciado entre peticiones."""
    registers = [e.register for e in profile.entities if e.poll is tier]
    return len(plan_blocks(registers, profile.max_gap, profile.max_block_registers)) * profile.min_request_interval_s


def request_rate(profile: DeviceProfile, intervals: Mapping[PollTier, int]) -> float:
    """Peticiones por segundo que piden los tiers con estos intervalos. El equipo admite 1."""
    return sum(min_tier_interval(profile, tier) / interval for tier, interval in intervals.items())
