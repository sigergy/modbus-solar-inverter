"""Diagnostics de un equipo: perfil, intervalos, estado de cada tier y palabras crudas."""

from collections.abc import Mapping
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST

from .runtime import DeviceRuntime

TO_REDACT = {CONF_HOST}


def device_diagnostics(runtime: DeviceRuntime, subentry_data: Mapping[str, Any]) -> dict[str, Any]:
    tiers = {
        tier.value: {
            "last_update_success": coordinator.last_update_success,
            "last_error": coordinator.last_error,
            "last_error_at": coordinator.last_error_at.isoformat() if coordinator.last_error_at else None,
        }
        for tier, coordinator in runtime.coordinators.items()
    }
    entities: dict[str, Any] = {}
    for spec in runtime.profile.entities:
        # data guarda el último TierResult correcto, también tras un fallo
        result = runtime.coordinators[spec.poll].data
        raw = result.raw.get(spec.key) if result is not None else None
        reg = spec.register
        entities[spec.key] = {
            "address": reg.address,
            "dtype": reg.dtype.value,
            "word_order": reg.word_order.value,
            "scale": reg.scale,
            "raw": list(raw) if raw is not None else None,
            "value": result.values.get(spec.key) if result is not None else None,
        }
    return {
        "subentry": async_redact_data(dict(subentry_data), TO_REDACT),
        "profile": runtime.profile.id,
        "intervals": runtime.intervals,
        "tiers": tiers,
        "entities": entities,
    }
