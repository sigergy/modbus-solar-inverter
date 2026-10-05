"""Construye las entidades de un equipo a partir de su perfil."""

from homeassistant.components.number import NumberEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components.switch import SwitchEntity

from ....domain.profile import EntitySpec
from ....domain.types import Platform
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity
from .energy import ModbusSolarEnergySensor
from .number import ModbusSolarNumber
from .switch import ModbusSolarSwitch


class ModbusSolarSensor(ModbusSolarEntity, SensorEntity):
    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: EntitySpec) -> None:
        super().__init__(coordinator, runtime, spec)
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


def build_sensors(runtime: DeviceRuntime) -> list[SensorEntity]:
    sensors: list[SensorEntity] = [
        ModbusSolarSensor(runtime.coordinators[spec.poll], runtime, spec)
        for spec in runtime.selection.entities
        if spec.platform is Platform.SENSOR
    ]
    by_key = {spec.key: spec for spec in runtime.selection.entities}
    for energy in runtime.selection.energies:
        # validate_profile garantiza que todas las fuentes van en el mismo tier
        coordinator = runtime.coordinators[by_key[energy.sources[0]].poll]
        sensors.append(ModbusSolarEnergySensor(coordinator, runtime, energy))
    return sensors


def _control_coordinator(runtime: DeviceRuntime) -> TierCoordinator:
    # los controles cuelgan del tier de la entidad de prueba: si el equipo no responde, no se ofrece escribir
    probe = next(e for e in runtime.profile.entities if e.key == runtime.profile.probe_key)
    return runtime.coordinators[probe.poll]


def build_numbers(runtime: DeviceRuntime) -> list[NumberEntity]:
    coordinator = _control_coordinator(runtime)
    return [ModbusSolarNumber(coordinator, runtime, spec) for spec in runtime.selection.controls]


def build_switches(runtime: DeviceRuntime) -> list[SwitchEntity]:
    coordinator = _control_coordinator(runtime)
    return [ModbusSolarSwitch(coordinator, runtime, spec) for spec in runtime.selection.controls]
