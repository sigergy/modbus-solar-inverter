"""Sensor de energía calculada: integra la suma de sus fuentes de potencia."""

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from ....domain.energy import EnergyAccumulator, EnergySpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


class ModbusSolarEnergySensor(ModbusSolarEntity, RestoreSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: EnergySpec) -> None:
        super().__init__(coordinator, runtime, spec)
        self._energy = spec
        # tres intervalos sin muestra = hueco que no se integra
        self._max_gap_s = 3 * runtime.intervals[coordinator.tier]
        self._accumulator = EnergyAccumulator(spec.sign, self._max_gap_s)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and isinstance(last.native_value, int | float):
            # lo que pasa con HA apagado no se integra: se sigue desde el último total
            self._accumulator = EnergyAccumulator(self._energy.sign, self._max_gap_s, float(last.native_value))
        self._sample()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sample()
        super()._handle_coordinator_update()

    def _sample(self) -> None:
        self._accumulator.add(dt_util.utcnow().timestamp(), self._source_power())

    def _source_power(self) -> float | None:
        data = self.coordinator.data
        if not self.coordinator.last_update_success or data is None:
            return None
        values = [data.values.get(key) for key in self._energy.sources]
        # una fuente sin valor (decode o lectura fallida) corta la serie
        if any(not isinstance(value, int | float) for value in values):
            return None
        return float(sum(values))

    @property
    def native_value(self) -> float:
        return self._accumulator.total_kwh
