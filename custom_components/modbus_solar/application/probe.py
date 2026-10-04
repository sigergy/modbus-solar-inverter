"""Validación de un equipo nuevo: lectura de la entidad de prueba del perfil."""

from ..domain.decode import decode
from ..domain.profile import DeviceProfile
from ..ports.device import DeviceGateway


async def probe_device(gateway: DeviceGateway, profile: DeviceProfile) -> None:
    spec = next(e for e in profile.entities if e.key == profile.probe_key)
    words = await gateway.read([spec.register])
    # DecodeError si el valor no es válido (por ejemplo, fuera del enum)
    decode(spec, words[spec.register])
