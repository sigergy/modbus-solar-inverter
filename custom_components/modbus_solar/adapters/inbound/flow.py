"""Config flow: una entry por inversor. Catálogo y gateway los inyecta config_flow.py."""

import asyncio
from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from typing import Any, ClassVar

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.translation import async_get_translations

from ...application.catalog import Catalog
from ...application.poller import TierResult, min_tier_interval
from ...application.probe import ProbeResult, probe_device
from ...const import (
    BRAND_TITLES,
    CONF_INTERVALS,
    CONF_PROFILE,
    CONF_UNIT_ID,
    DEFAULT_INTERVALS,
    DOMAIN,
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

CONF_ADVANCED = "advanced"
CONF_BRAND = "brand"
# segundos máximos de la sonda: un equipo que no contesta no deja el formulario cargando
PROBE_TIMEOUT_S = 20


def device_unique_id(host: str, port: int, unit_id: int) -> str:
    return f"{host.lower()}:{port}:{unit_id}"


def profile_option(profile_id: str) -> str:
    """Clave y valor del selector de modelo: el id sin puntos, válido como translation_key."""
    return profile_id.replace(".", "_")


def format_readings(profile: DeviceProfile, result: TierResult, translations: Mapping[str, str]) -> str:
    """Lista markdown de las lecturas de la sonda, con nombres y estados traducidos."""
    prefix = f"component.{DOMAIN}.entity.sensor"
    lines: list[str] = []
    for spec in profile.entities:
        if spec.key not in result.values:
            continue
        value = result.values[spec.key]
        if value is None:
            text = "—"
        elif spec.enum is not None:
            text = translations.get(f"{prefix}.{spec.key}.state.{value}", str(value))
        else:
            text = f"{value} {spec.unit}" if spec.unit else str(value)
        lines.append(f"- {translations.get(f'{prefix}.{spec.key}.name', spec.key)}: {text}")
    return "\n".join(lines)


class DeviceConfigFlow(ConfigFlow):
    """Alta de un inversor: modelo, conexión validada con una lectura real y nombre."""

    VERSION = 2
    catalog: ClassVar[Catalog]
    gateway_factory: ClassVar[GatewayFactory]

    _brand: str
    _profile: DeviceProfile
    _connection: dict[str, Any]
    _readings: str

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._brand = user_input[CONF_BRAND]
            return await self.async_step_model()
        options = [SelectOptionDict(value=b, label=BRAND_TITLES[b]) for b in self.catalog.brands()]
        selector = SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST))
        return self.async_show_form(step_id="user", data_schema=vol.Schema({vol.Required(CONF_BRAND): selector}))

    async def async_step_model(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        profiles = self.catalog.for_brand(self._brand)
        if user_input is not None:
            # la opción lleva el id sin puntos: se deshace buscando entre los perfiles de la marca
            self._profile = next(p for p in profiles if profile_option(p.id) == user_input[CONF_PROFILE])
            return await self.async_step_connection()
        options = [SelectOptionDict(value=profile_option(p.id), label=profile_option(p.id)) for p in profiles]
        selector = SelectSelector(
            SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST, translation_key="profile")
        )
        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema({vol.Required(CONF_PROFILE): selector}),
            description_placeholders={"brand": BRAND_TITLES[self._brand]},
        )

    async def async_step_connection(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        profile = self._profile
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_ADVANCED][CONF_PORT]
            unit_id = user_input[CONF_ADVANCED][CONF_UNIT_ID]
            # el duplicado se detecta antes de abrir conexión
            await self.async_set_unique_id(device_unique_id(host, port, unit_id))
            self._abort_if_unique_id_configured()
            try:
                result = await self._probe(host, port, unit_id, profile)
            except EndpointInUse:
                errors["base"] = "endpoint_in_use"
            except DeviceUnavailable, TimeoutError:
                errors["base"] = "cannot_connect"
            except DeviceProtocolError, DecodeError:
                errors["base"] = "invalid_response"
            else:
                self._connection = {CONF_HOST: host, CONF_PORT: port, CONF_UNIT_ID: unit_id}
                translations = await async_get_translations(self.hass, self.hass.config.language, "entity", {DOMAIN})
                self._readings = format_readings(profile, result.readings, translations)
                return await self.async_step_confirm()
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_ADVANCED): section(
                    vol.Schema(
                        {
                            vol.Required(CONF_PORT, default=profile.default_port): PORT,
                            vol.Required(CONF_UNIT_ID, default=profile.default_unit_id): UNIT_ID,
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )
        return self.async_show_form(
            step_id="connection",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        profile = self._profile
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    **self._connection,
                    CONF_PROFILE: profile.id,
                    CONF_INTERVALS: dict(DEFAULT_INTERVALS),
                },
            )
        default_name = f"{BRAND_TITLES[profile.brand]} {profile.models[0]}"
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default=default_name): str}),
            description_placeholders={CONF_HOST: self._connection[CONF_HOST], "readings": self._readings},
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        profile = self.catalog.get(entry.data[CONF_PROFILE])
        errors: dict[str, str] = {}
        if user_input is not None:
            # cada tier tiene que caber en su intervalo con el espaciado entre peticiones
            for tier in PollTier:
                if user_input[tier.value] < min_tier_interval(profile, tier):
                    errors[tier.value] = "interval_too_short"
            if not errors:
                host, port = user_input[CONF_HOST], user_input[CONF_PORT]
                unique_id = device_unique_id(host, port, entry.data[CONF_UNIT_ID])
                if any(
                    e.unique_id == unique_id and e.entry_id != entry.entry_id for e in self._async_current_entries()
                ):
                    return self.async_abort(reason="already_configured")
                # actualiza la entry y la recarga: abre la conexión con el endpoint nuevo
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    data_updates={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_INTERVALS: {tier.value: user_input[tier.value] for tier in PollTier},
                    },
                )
        current = {
            CONF_HOST: entry.data[CONF_HOST],
            CONF_PORT: entry.data[CONF_PORT],
            **DEFAULT_INTERVALS,
            **entry.data.get(CONF_INTERVALS, {}),
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

    async def _probe(self, host: str, port: int, unit_id: int, profile: DeviceProfile) -> ProbeResult:
        async with asyncio.timeout(PROBE_TIMEOUT_S):
            async with self.gateway_factory(self.hass, host, port, unit_id, profile) as gateway:
                return await probe_device(gateway, profile)
