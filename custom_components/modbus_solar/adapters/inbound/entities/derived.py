"""Potencia derivada: la fuente leída filtrada por signo (importada, exportada, generador)."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfPower

from ....domain.energy import filter_power
from ....domain.metering import DerivedPowerSpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


class ModbusSolarDerivedPowerSensor(ModbusSolarEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: DerivedPowerSpec) -> None:
        super().__init__(coordinator, runtime, spec)
        self._power = spec

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data is None:
            return None
        value = data.values.get(self._power.source)
        # una fuente sin valor (decode o lectura fallida) deja la potencia sin valor
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        return filter_power(float(value), self._power.sign)
