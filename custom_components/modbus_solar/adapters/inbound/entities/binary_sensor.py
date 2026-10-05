"""Entidad binary_sensor: un bit de un registro, ya decodificado a bool por el coordinator."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from ....domain.profile import EntitySpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity


class ModbusSolarBinarySensor(ModbusSolarEntity, BinarySensorEntity):
    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: EntitySpec) -> None:
        super().__init__(coordinator, runtime, spec)
        # domain guarda cadenas; aquí se convierte al enum de HA
        if spec.device_class is not None:
            self._attr_device_class = BinarySensorDeviceClass(spec.device_class)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.values.get(self._spec.key)
        return None if value is None else bool(value)
