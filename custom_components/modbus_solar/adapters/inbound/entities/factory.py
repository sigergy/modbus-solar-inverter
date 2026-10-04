"""Construye las entidades de un equipo a partir de su perfil."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass

from ....domain.profile import EntitySpec
from ....domain.types import Platform
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


class ModbusSolarSensor(ModbusSolarEntity, SensorEntity):
    def __init__(
        self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: EntitySpec, brand_entry_id: str
    ) -> None:
        super().__init__(coordinator, runtime, spec, brand_entry_id)
        # domain guarda cadenas; aquí se convierten a los enums de HA
        if spec.device_class is not None:
            self._attr_device_class = SensorDeviceClass(spec.device_class)
        if spec.state_class is not None:
            self._attr_state_class = SensorStateClass(spec.state_class)
        self._attr_native_unit_of_measurement = spec.unit
        if spec.enum is not None:
            self._attr_options = list(spec.enum.values())

    @property
    def native_value(self) -> int | float | str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.values.get(self._spec.key)


def build_sensors(runtime: DeviceRuntime, brand_entry_id: str) -> list[ModbusSolarSensor]:
    return [
        ModbusSolarSensor(runtime.coordinators[spec.poll], runtime, spec, brand_entry_id)
        for spec in runtime.profile.entities
        if spec.platform is Platform.SENSOR
    ]
