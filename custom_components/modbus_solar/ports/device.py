"""Puertos de salida: lectura y escritura de registros de un equipo."""

from collections.abc import Mapping, Sequence
from typing import Protocol

from ..domain.control import WriteSpec
from ..domain.profile import RegisterSpec


class DeviceGateway(Protocol):
    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]:
        """Palabras crudas por registro. Lanza DeviceUnavailable o DeviceProtocolError."""
        ...


class DeviceWriter(Protocol):
    """Separado de DeviceGateway: el poller y el config flow solo leen."""

    async def write(self, spec: WriteSpec, value: float) -> None:
        """Escribe el valor ya validado. Lanza EncodeError, DeviceUnavailable o DeviceProtocolError."""
        ...
