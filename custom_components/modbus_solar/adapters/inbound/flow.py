"""Config flow de marca y subentry flow de equipo. Catálogo y gateway los inyecta config_flow.py."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, ClassVar

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback

from ...application.catalog import Catalog
from ...application.poller import min_tier_interval
from ...application.probe import probe_device
from ...const import (
    BRAND_TITLES,
    CONF_BRAND,
    CONF_INTERVALS,
    CONF_PROFILE,
    CONF_UNIT_ID,
    DEFAULT_INTERVALS,
    SUBENTRY_DEVICE,
)
from ...domain.errors import DecodeError, DeviceProtocolError, DeviceUnavailable, EndpointInUse
from ...domain.profile import DeviceProfile
from ...domain.types import PollTier
from ...ports.device import DeviceGateway

# (hass, host, port, unit_id, profile) -> contexto que entrega un gateway sobre una unit temporal
type GatewayFactory = Callable[
    [HomeAssistant, str, int, int, DeviceProfile], AbstractAsyncContextManager[DeviceGateway]
]

PORT = vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))
UNIT_ID = vol.All(vol.Coerce(int), vol.Range(min=1, max=247))
INTERVAL = vol.All(vol.Coerce(int), vol.Range(min=1))


def device_unique_id(host: str, port: int, unit_id: int) -> str:
    return f"{host.lower()}:{port}:{unit_id}"


class BrandFlow(ConfigFlow):
    """Una entry por marca, sin datos de conexión: los equipos son subentries."""

    VERSION = 1
    catalog: ClassVar[Catalog]
    device_flow: ClassVar[type[ConfigSubentryFlow]]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            brand = user_input[CONF_BRAND]
            await self.async_set_unique_id(brand)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=BRAND_TITLES[brand], data={CONF_BRAND: brand})
        brands = {brand: BRAND_TITLES[brand] for brand in self.catalog.brands()}
        schema = vol.Schema({vol.Required(CONF_BRAND): vol.In(brands)})
        return self.async_show_form(step_id="user", data_schema=schema)

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_DEVICE: cls.device_flow}


class DeviceSubentryFlow(ConfigSubentryFlow):
    """Alta de un equipo: valida la conexión leyendo la entidad probe_key del perfil."""

    catalog: ClassVar[Catalog]
    gateway_factory: ClassVar[GatewayFactory]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        profiles = self.catalog.for_brand(entry.data[CONF_BRAND])
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port, unit_id = user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_UNIT_ID]
            profile = self.catalog.get(user_input[CONF_PROFILE])
            unique_id = device_unique_id(host, port, unit_id)
            # el duplicado se detecta antes de abrir conexión
            if self._unique_id_taken(entry, unique_id):
                return self.async_abort(reason="already_configured")
            error = await self._probe(host, port, unit_id, profile)
            if error is None:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    unique_id=unique_id,
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                        CONF_PROFILE: profile.id,
                        CONF_INTERVALS: dict(DEFAULT_INTERVALS),
                    },
                )
            errors["base"] = error
        default = profiles[0]
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=default.default_port): PORT,
                vol.Required(CONF_UNIT_ID, default=default.default_unit_id): UNIT_ID,
                vol.Required(CONF_PROFILE, default=default.id): vol.In({p.id: ", ".join(p.models) for p in profiles}),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        profile = self.catalog.get(subentry.data[CONF_PROFILE])
        errors: dict[str, str] = {}
        if user_input is not None:
            # cada tier tiene que caber en su intervalo con el espaciado entre peticiones
            for tier in PollTier:
                if user_input[tier.value] < min_tier_interval(profile, tier):
                    errors[tier.value] = "interval_too_short"
            if not errors:
                host, port = user_input[CONF_HOST], user_input[CONF_PORT]
                unique_id = device_unique_id(host, port, subentry.data[CONF_UNIT_ID])
                if self._unique_id_taken(entry, unique_id, exclude=subentry.subentry_id):
                    return self.async_abort(reason="already_configured")
                return self.async_update_and_abort(
                    entry,
                    subentry,
                    unique_id=unique_id,
                    data_updates={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_INTERVALS: {tier.value: user_input[tier.value] for tier in PollTier},
                    },
                )
        current = {
            CONF_HOST: subentry.data[CONF_HOST],
            CONF_PORT: subentry.data[CONF_PORT],
            **DEFAULT_INTERVALS,
            **subentry.data.get(CONF_INTERVALS, {}),
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT): PORT,
                **{vol.Required(tier.value): INTERVAL for tier in PollTier},
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or current),
            errors=errors,
        )

    @staticmethod
    def _unique_id_taken(entry: ConfigEntry, unique_id: str, exclude: str | None = None) -> bool:
        return any(s.unique_id == unique_id and s.subentry_id != exclude for s in entry.subentries.values())

    async def _probe(self, host: str, port: int, unit_id: int, profile: DeviceProfile) -> str | None:
        """Clave del error del formulario, o None si el equipo responde bien."""
        try:
            async with self.gateway_factory(self.hass, host, port, unit_id, profile) as gateway:
                await probe_device(gateway, profile)
        except EndpointInUse:
            return "endpoint_in_use"
        except DeviceUnavailable:
            return "cannot_connect"
        except DeviceProtocolError, DecodeError:
            return "invalid_response"
        return None
