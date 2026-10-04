"""Base de number y switch de un control: comparten estado, escritor y traducción de errores."""

from collections.abc import Iterator
from contextlib import contextmanager

from homeassistant.exceptions import HomeAssistantError

from ....const import DOMAIN
from ....domain.control import GatedLimitSpec
from ....domain.errors import DeviceProtocolError, DeviceUnavailable, EncodeError
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


@contextmanager
def write_errors() -> Iterator[None]:
    """Traduce los errores de escritura del dominio a HomeAssistantError con mensaje traducible."""
    try:
        yield
    except (DeviceUnavailable, DeviceProtocolError, EncodeError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="write_failed", translation_placeholders={"error": str(err)}
        ) from err


class ModbusSolarControl(ModbusSolarEntity):
    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: GatedLimitSpec, key: str) -> None:
        super().__init__(coordinator, runtime, spec, key)
        self._control = spec
        self._writer = runtime.writer
        # el number y el switch del mismo control comparten el estado
        self._state = runtime.control_states[spec.key]
