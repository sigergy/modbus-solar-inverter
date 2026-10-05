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


def device_info(
    entry_id: str, profile: DeviceProfile, component: Component, device_id: int | None, serial: str | None
) -> DeviceInfo:
    """Dispositivo de un componente: el principal lleva el número de serie; el resto cuelga de él."""
    main = component is Component.MAIN
    key = profile.device_type if main else component.value
    # mismo identificador que borra _remove_unselected al deseleccionar el componente
    info = DeviceInfo(
        identifiers={(DOMAIN, entry_id if main else f"{entry_id}_{component.value}")},
        translation_key=key if device_id is None else f"{key}_numbered",
        translation_placeholders=None if device_id is None else {"device_id": str(device_id)},
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
        self._attr_device_info = device_info(
            runtime.entry_id, runtime.profile, spec.component, runtime.device_id, runtime.serial_number
        )

    @property
    def available(self) -> bool:
        # hasta la primera lectura correcta no hay datos: la entidad nace unavailable
        return super().available and self.coordinator.data is not None
