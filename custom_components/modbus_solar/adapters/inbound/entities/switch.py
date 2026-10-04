"""Switch de un control: con él activo el equipo recibe el límite; apagado, off_value."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.restore_state import RestoreEntity

from ....application.control import set_enabled
from ....domain.control import GatedLimitSpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .control import ModbusSolarControl, write_errors


class ModbusSolarSwitch(ModbusSolarControl, SwitchEntity, RestoreEntity):
    # el equipo no permite leer el ajuste: HA muestra lo último que escribió, no lo que hay
    _attr_assumed_state = True

    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: GatedLimitSpec) -> None:
        super().__init__(coordinator, runtime, spec, spec.switch_key)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        # la restauración no escribe al equipo: tras reiniciar HA el inversor conserva lo que tenía
        if last is not None and last.state in (STATE_ON, STATE_OFF):
            self._state.enabled = last.state == STATE_ON

    @property
    def is_on(self) -> bool:
        return self._state.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, enabled: bool) -> None:
        with write_errors():
            await set_enabled(self._writer, self._control, self._state, enabled)
        self.async_write_ha_state()
