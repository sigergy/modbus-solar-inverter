"""Entidad base: dispositivo, unique_id y disponibilidad según el coordinator de su tier."""

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ....const import BRAND_TITLES, DOMAIN
from ....domain.control import GatedLimitSpec
from ....domain.energy import EnergySpec
from ....domain.profile import DeviceProfile, EntitySpec
from ....domain.types import Component
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime, entity_unique_id


def device_info(entry_id: str, profile: DeviceProfile, component: Component, serial: str | None) -> DeviceInfo:
    """Dispositivo de un componente: el principal lleva el número de serie; el resto cuelga de él.

    El nombre no lleva el Device ID: el ID va solo en el entity_id (ver suggested_object_id).
    """
    main = component is Component.MAIN
    key = profile.device_type if main else component.value
    # mismo identificador que borra _remove_unselected al deseleccionar el componente
    info = DeviceInfo(
        identifiers={(DOMAIN, entry_id if main else f"{entry_id}_{component.value}")},
        translation_key=key,
        manufacturer=BRAND_TITLES[profile.brand],
        model=profile.models[0],
    )
    if main:
        if serial:
            info["serial_number"] = serial
    else:
        info["via_device"] = (DOMAIN, entry_id)
    return info


class ModbusSolarEntity(CoordinatorEntity[TierCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TierCoordinator,
        runtime: DeviceRuntime,
        spec: EntitySpec | EnergySpec | GatedLimitSpec,
        key: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._spec = spec
        # un control da dos entidades (number y switch): la clave la elige quien construye
        key = spec.key if key is None else key
        self._attr_translation_key = key
        self._attr_unique_id = entity_unique_id(runtime.entry_id, key)
        self._attr_entity_registry_enabled_default = spec.enabled_default
        # las energías calculadas no tienen categoría: son de primer nivel
        if isinstance(spec, EntitySpec) and spec.entity_category is not None:
            self._attr_entity_category = EntityCategory(spec.entity_category)
        self._device_id = runtime.device_id
        self._attr_device_info = device_info(runtime.entry_id, runtime.profile, spec.component, runtime.serial_number)

    @property
    def suggested_object_id(self) -> str | None:
        """Base del entity_id con el Device ID delante del nombre de la entidad.

        HA antepone el nombre del dispositivo a esta base (has_entity_name), así que el
        entity_id queda «<dispositivo> <ID> <entidad>», como el prefijo de device_label
        que usa el renombrado de reconfigure. Solo cuenta en el alta en el registro.
        """
        name = super().suggested_object_id
        if self._device_id is None:
            return name
        return f"{self._device_id} {name}" if name else str(self._device_id)

    @property
    def available(self) -> bool:
        # hasta la primera lectura correcta no hay datos: la entidad nace unavailable
        return super().available and self.coordinator.data is not None
