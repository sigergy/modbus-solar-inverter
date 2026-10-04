"""Entidad base: dispositivo, unique_id y disponibilidad según el coordinator de su tier."""

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ....const import BRAND_TITLES, DOMAIN
from ....domain.energy import EnergySpec
from ....domain.profile import EntitySpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime, entity_unique_id


class ModbusSolarEntity(CoordinatorEntity[TierCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: EntitySpec | EnergySpec) -> None:
        super().__init__(coordinator)
        self._spec = spec
        self._attr_translation_key = spec.key
        self._attr_unique_id = entity_unique_id(runtime.entry_id, spec.key)
        self._attr_entity_registry_enabled_default = spec.enabled_default
        # las energías calculadas no tienen categoría: son de primer nivel
        if isinstance(spec, EntitySpec) and spec.entity_category is not None:
            self._attr_entity_category = EntityCategory(spec.entity_category)
        profile = runtime.profile
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry_id)},
            name=runtime.title,
            manufacturer=BRAND_TITLES[profile.brand],
            model=profile.models[0],
        )

    @property
    def available(self) -> bool:
        # hasta la primera lectura correcta no hay datos: la entidad nace unavailable
        return super().available and self.coordinator.data is not None
