"""Number del límite de un control: potencia máxima que se escribe al equipo si el switch está activo."""

from homeassistant.components.number import NumberDeviceClass, NumberMode, RestoreNumber

from ....application.control import set_limit
from ....domain.control import GatedLimitSpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .control import ModbusSolarControl, write_errors


class ModbusSolarNumber(ModbusSolarControl, RestoreNumber):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: GatedLimitSpec) -> None:
        super().__init__(coordinator, runtime, spec, spec.key)
        self._attr_native_min_value = spec.min_value
        self._attr_native_max_value = spec.max_value
        self._attr_native_step = spec.step
        self._attr_native_unit_of_measurement = spec.unit
        if spec.device_class is not None:
            self._attr_device_class = NumberDeviceClass(spec.device_class)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        # el equipo no permite leer el ajuste: se recupera lo que HA mostraba y no se escribe nada
        if last is not None and isinstance(last.native_value, int | float):
            if self._control.min_value <= last.native_value <= self._control.max_value:
                self._state.limit = float(last.native_value)

    @property
    def native_value(self) -> float:
        return self._state.limit

    async def async_set_native_value(self, value: float) -> None:
        with write_errors():
            await set_limit(self._writer, self._control, self._state, value)
        self.async_write_ha_state()
