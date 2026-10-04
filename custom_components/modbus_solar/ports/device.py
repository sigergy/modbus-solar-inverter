"""Puerto de salida: lectura de registros de un equipo."""

from collections.abc import Mapping, Sequence
from typing import Protocol

from ..domain.profile import RegisterSpec


class DeviceGateway(Protocol):
    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]:
        """Palabras crudas por registro. Lanza DeviceUnavailable o DeviceProtocolError."""
        ...
