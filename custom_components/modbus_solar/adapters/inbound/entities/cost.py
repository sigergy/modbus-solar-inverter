"""Sensor de coste: la energía de su fuente por el precio fijo o el de una entidad de HA."""

import logging
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from ....domain.cost import CostAccumulator, price_per_kwh
from ....domain.metering import DerivedCostSpec
from ..coordinator import TierCoordinator
from ..runtime import DeviceRuntime
from .base import ModbusSolarEntity

_LOGGER = logging.getLogger(__name__)


class ModbusSolarCostSensor(ModbusSolarEntity, RestoreSensor):
    _attr_device_class = SensorDeviceClass.MONETARY
    # HA no admite total_increasing con monetary; además un precio negativo resta
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "EUR"
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: TierCoordinator, runtime: DeviceRuntime, spec: DerivedCostSpec, price: Mapping[str, Any]
    ) -> None:
        super().__init__(coordinator, runtime, spec)
        self._cost = spec
        self._price = price
        # tres intervalos sin muestra = hueco que no se cobra, como la energía
        self._max_gap_s = 3 * runtime.intervals[coordinator.tier]
        self._accumulator = CostAccumulator(spec.sign, self._max_gap_s)
        self._price_missing = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and isinstance(last.native_value, int | float | Decimal):
            self._accumulator = CostAccumulator(self._cost.sign, self._max_gap_s, float(last.native_value))
        self._sample()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sample()
        super()._handle_coordinator_update()

    def _sample(self) -> None:
        price = self._current_price()
        # un aviso por caída del precio, no por muestra
        if price is None and not self._price_missing:
            _LOGGER.warning(
                "%s: price from %s unavailable; the energy stays pending", self.entity_id, self._price.get("entity_id")
            )
        elif price is not None and self._price_missing:
            _LOGGER.info("%s: price from %s back", self.entity_id, self._price.get("entity_id"))
        self._price_missing = price is None
        self._accumulator.add(dt_util.utcnow().timestamp(), self._source_power(), price)

    def _current_price(self) -> float | None:
        if self._price["mode"] == "fixed":
            return float(self._price["price"])
        state = self.hass.states.get(self._price["entity_id"])
        if state is None:
            return None
        return price_per_kwh(state.state, state.attributes.get("unit_of_measurement"))

    def _source_power(self) -> float | None:
        data = self.coordinator.data
        if not self.coordinator.last_update_success or data is None:
            return None
        value = data.values.get(self._cost.source)
        # una fuente sin valor (decode o lectura fallida) corta la serie
        return float(value) if isinstance(value, int | float) else None

    @property
    def native_value(self) -> float:
        return self._accumulator.total_eur
