"""Validación de un equipo nuevo: entidad de prueba, lecturas fast + instant y número de serie."""

from dataclasses import dataclass

from ..domain.decode import decode, decode_text
from ..domain.errors import DecodeError, DeviceProtocolError, DeviceUnavailable
from ..domain.profile import DeviceProfile
from ..domain.types import PollTier
from ..ports.device import DeviceGateway
from .poller import TierResult, read_tier


@dataclass(frozen=True)
class ProbeResult:
    readings: TierResult  # fast + instant: lo que coteja el paso de lecturas
    serial: str | None


async def probe_device(gateway: DeviceGateway, profile: DeviceProfile) -> ProbeResult:
    spec = next(e for e in profile.entities if e.key == profile.probe_key)
    words = await gateway.read([spec.register])
    # DecodeError si el valor no es válido (por ejemplo, fuera del enum)
    decode(spec, words[spec.register])
    keys = {e.key for e in profile.entities if e.enabled_default}
    fast = await read_tier(PollTier.FAST, gateway, profile, keys)
    instant = await read_tier(PollTier.INSTANT, gateway, profile, keys)
    readings = TierResult(
        values=fast.values | instant.values,
        raw=fast.raw | instant.raw,
        decode_errors=fast.decode_errors | instant.decode_errors,
    )
    return ProbeResult(readings=readings, serial=await _read_serial(gateway, profile))


async def _read_serial(gateway: DeviceGateway, profile: DeviceProfile) -> str | None:
    if profile.serial is None:
        return None
    try:
        words = await gateway.read([profile.serial])
        return decode_text(profile.serial, words[profile.serial]) or None
    except DecodeError, DeviceUnavailable, DeviceProtocolError:
        # el número de serie es opcional: su fallo no invalida la sonda
        return None
