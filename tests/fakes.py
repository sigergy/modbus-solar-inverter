"""Dobles de prueba compartidos por tests/unit y tests/ha."""

from collections.abc import Mapping, Sequence

from custom_components.modbus_solar.domain.control import WriteSpec
from custom_components.modbus_solar.domain.profile import RegisterSpec

# palabras crudas del Ingeteam por dirección: grid_connected, 5000.0 Wh y 1234.5 W
INGETEAM_WORDS: dict[int, tuple[int, ...]] = {0x101D: (3,), 0x1021: (0, 50000), 0x1037: (0, 12345)}


class FakeGateway:
    """DeviceGateway en memoria: devuelve `words[address]` o lanza `error`."""

    def __init__(self, words: Mapping[int, tuple[int, ...]], error: Exception | None = None) -> None:
        self.words = dict(words)
        self.error = error
        self.calls: list[tuple[RegisterSpec, ...]] = []

    async def read(self, specs: Sequence[RegisterSpec]) -> Mapping[RegisterSpec, tuple[int, ...]]:
        self.calls.append(tuple(specs))
        if self.error is not None:
            raise self.error
        return {spec: self.words[spec.address] for spec in specs}


class FakeWriter:
    """DeviceWriter en memoria: anota (spec, valor) o lanza `error`."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.writes: list[tuple[WriteSpec, float]] = []

    async def write(self, spec: WriteSpec, value: float) -> None:
        if self.error is not None:
            raise self.error
        self.writes.append((spec, value))
