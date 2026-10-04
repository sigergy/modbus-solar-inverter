"""Validación de un equipo nuevo: entidad de prueba y lecturas del tier fast."""

from ..domain.decode import decode
from ..domain.profile import DeviceProfile
from ..domain.types import PollTier
from ..ports.device import DeviceGateway
from .poller import TierResult, read_tier


async def probe_device(gateway: DeviceGateway, profile: DeviceProfile) -> TierResult:
    spec = next(e for e in profile.entities if e.key == profile.probe_key)
    words = await gateway.read([spec.register])
    # DecodeError si el valor no es válido (por ejemplo, fuera del enum)
    decode(spec, words[spec.register])
    # lecturas que muestra el paso de confirmación del config flow
    keys = {e.key for e in profile.entities if e.enabled_default}
    return await read_tier(PollTier.FAST, gateway, profile, keys)
