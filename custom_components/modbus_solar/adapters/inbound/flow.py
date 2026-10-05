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
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from homeassistant.helpers.translation import async_get_translations

from ...application.catalog import Catalog
from ...application.poller import min_tier_interval
from ...application.probe import ProbeResult, probe_device
from ...application.selection import Selection, select
from ...const import (
    BRAND_TITLES,
    CONF_COMPONENTS,
    CONF_DEVICE_ID,
    CONF_INTERVALS,
    CONF_PROFILE,
    CONF_SERIAL_NUMBER,
    CONF_UNIT_ID,
    DEFAULT_INTERVALS,
    DOMAIN,
)
from ...domain.errors import DecodeError, DeviceProtocolError, DeviceUnavailable, EndpointInUse
from ...domain.profile import DeviceProfile
from ...domain.types import Component, Platform, PollTier
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


def valid_serial(value: str) -> bool:
    """Número de serie escrito: solo letras y números ASCII, sin espacios."""
    return value.isascii() and value.isalnum()


def used_device_ids(hass: HomeAssistant, catalog: Catalog, device_type: str, exclude: str | None = None) -> set[int]:
    """Device ID de las entries del mismo device_type. Sin ID o con perfil desconocido no cuentan."""
    used: set[int] = set()
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == exclude or CONF_DEVICE_ID not in entry.data:
            continue
        try:
            profile = catalog.get(entry.data[CONF_PROFILE])
        except KeyError:
            continue
        if profile.device_type == device_type:
            used.add(int(entry.data[CONF_DEVICE_ID]))
    return used


def free_device_id(hass: HomeAssistant, catalog: Catalog, device_type: str, exclude: str | None = None) -> int:
    """Menor entero >= 0 que no usa otra entry del mismo device_type."""
    used = used_device_ids(hass, catalog, device_type, exclude)
    return next(n for n in range(len(used) + 1) if n not in used)


def profile_option(profile_id: str) -> str:
    """Clave y valor del selector de modelo: el id sin puntos, válido como translation_key."""
    return profile_id.replace(".", "_")


def format_number(value: float, language: str) -> str:
    """Separador de miles según el idioma: coma en inglés; punto de miles y coma decimal en español."""
    text = f"{value:,}"
    if language.split("-")[0].lower() == "es":
        text = text.translate(str.maketrans(",.", ".,"))
    return text


def format_readings(
    profile: DeviceProfile,
    selection: Selection,
    result: ProbeResult,
    translations: Mapping[str, str],
    language: str,
) -> str:
    """Lecturas de la sonda agrupadas por componente, con nombres y estados traducidos."""
    prefix = f"component.{DOMAIN}.entity.sensor"
    values = result.readings.values
    groups: list[str] = []
    # primero el principal; después los opcionales en el orden del perfil
    for component in (Component.MAIN, *(c.component for c in profile.components)):
        lines: list[str] = []
        for spec in selection.entities:
            # solo sensores: los bits del BMS no se cotejan con la pantalla
            if spec.component is not component or spec.platform is not Platform.SENSOR or spec.key not in values:
                continue
            value = values[spec.key]
            if value is None:
                text = "—"
            elif spec.enum is not None:
                text = translations.get(f"{prefix}.{spec.key}.state.{value}", str(value))
            else:
                shown = (
                    format_number(value, language)
                    if isinstance(value, int | float) and not isinstance(value, bool)
                    else str(value)
                )
                text = f"{shown} {spec.unit}" if spec.unit else shown
            lines.append(f"- {translations.get(f'{prefix}.{spec.key}.name', spec.key)}: {text}")
        if lines:
            device = profile.device_type if component is Component.MAIN else component.value
            title = translations.get(f"component.{DOMAIN}.device.{device}.name", device)
            groups.append("\n".join([f"**{title}**", *lines]))
    return "\n\n".join(groups)


class DeviceConfigFlow(ConfigFlow):
    """Alta de un inversor: modelo, conexión validada con una lectura real y nombre."""

    VERSION = 2
    catalog: ClassVar[Catalog]
    gateway_factory: ClassVar[GatewayFactory]

    _brand: str
    _profile: DeviceProfile
    _connection: dict[str, Any] | None = None
    _probe: ProbeResult | None = None
    # None = aún sin elegir: el paso muestra los valores por defecto del perfil
    _components: list[Component] | None = None

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
        # al volver aquí desde las lecturas se olvidan las lecturas y los componentes
        self._probe = None
        self._components = None
        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema({vol.Required(CONF_PROFILE): self._profile_selector()}),
            description_placeholders={"brand": BRAND_TITLES[self._brand]},
        )

    def _profile_selector(self) -> SelectSelector:
        options = [
            SelectOptionDict(value=profile_option(p.id), label=profile_option(p.id))
            for p in self.catalog.for_brand(self._brand)
        ]
        return SelectSelector(
            SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST, translation_key="profile")
        )

    def _switch_profile(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Aplica el modelo elegido tras un error. Los puertos del modelo nuevo solo si no se tocaron."""
        option = user_input.get(CONF_PROFILE)
        old = self._profile
        profiles = self.catalog.for_brand(self._brand)
        new = old if option is None else next(p for p in profiles if profile_option(p.id) == option)
        if new is old:
            return user_input
        advanced = user_input[CONF_ADVANCED]
        untouched = (advanced[CONF_PORT], advanced[CONF_UNIT_ID]) == (old.default_port, old.default_unit_id)
        self._profile = new
        # los componentes elegidos eran de otro modelo
        self._components = None
        if untouched:
            return {**user_input, CONF_ADVANCED: {CONF_PORT: new.default_port, CONF_UNIT_ID: new.default_unit_id}}
        return user_input

    async def _translations(self) -> dict[str, str]:
        """Nombres de entidad y de dispositivo en el idioma de HA."""
        language = self.hass.config.language
        entity = await async_get_translations(self.hass, language, "entity", {DOMAIN})
        device = await async_get_translations(self.hass, language, "device", {DOMAIN})
        return {**entity, **device}

    async def async_step_connection(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = self._switch_profile(user_input)
            profile = self._profile
            host = user_input[CONF_HOST]
            port = user_input[CONF_ADVANCED][CONF_PORT]
            unit_id = user_input[CONF_ADVANCED][CONF_UNIT_ID]
            # el duplicado se detecta antes de abrir conexión
            await self.async_set_unique_id(device_unique_id(host, port, unit_id))
            self._abort_if_unique_id_configured()
            try:
                result = await self._probe_endpoint(host, port, unit_id, profile)
            except EndpointInUse:
                errors["base"] = "endpoint_in_use"
            except DeviceUnavailable, TimeoutError:
                errors["base"] = "cannot_connect"
            except DeviceProtocolError, DecodeError:
                errors["base"] = "invalid_response"
            else:
                self._connection = {CONF_HOST: host, CONF_PORT: port, CONF_UNIT_ID: unit_id}
                self._probe = result
                if profile.components:
                    return await self.async_step_components()
                self._components = []
                return await self.async_step_readings()
        else:
            # al volver desde las lecturas se olvidan estas y se conservan los componentes
            self._probe = None
        profile = self._profile
        fields: dict[Any, Any] = {vol.Required(CONF_HOST): str}
        if errors:
            # HA no ofrece botones secundarios en un formulario: el modelo se corrige aquí
            fields[vol.Required(CONF_PROFILE, default=profile_option(profile.id))] = self._profile_selector()
        fields[vol.Required(CONF_ADVANCED)] = section(
            vol.Schema(
                {
                    vol.Required(CONF_PORT, default=profile.default_port): PORT,
                    vol.Required(CONF_UNIT_ID, default=profile.default_unit_id): UNIT_ID,
                }
            ),
            {"collapsed": True},
        )
        suggested = user_input
        if suggested is None and self._connection is not None:
            suggested = {
                CONF_HOST: self._connection[CONF_HOST],
                CONF_ADVANCED: {CONF_PORT: self._connection[CONF_PORT], CONF_UNIT_ID: self._connection[CONF_UNIT_ID]},
            }
        shown = suggested or {}
        placeholders = {
            "brand": BRAND_TITLES[self._brand],
            "model": profile.models[0],
            CONF_HOST: shown.get(CONF_HOST, ""),
            CONF_PORT: str(shown.get(CONF_ADVANCED, {}).get(CONF_PORT, profile.default_port)),
            "timeout": str(PROBE_TIMEOUT_S),
        }
        return self.async_show_form(
            step_id="connection",
            data_schema=self.add_suggested_values_to_schema(vol.Schema(fields), suggested),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_components(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        profile = self._profile
        if user_input is not None:
            chosen = set(user_input[CONF_COMPONENTS])
            # en el orden del perfil
            self._components = [c.component for c in profile.components if c.component.value in chosen]
            return await self.async_step_readings()
        if self._components is None:
            default = [c.component.value for c in profile.components if c.default]
        else:
            default = [c.value for c in self._components]
        options = [SelectOptionDict(value=c.component.value, label=c.component.value) for c in profile.components]
        selector = SelectSelector(
            SelectSelectorConfig(
                options=options, multiple=True, mode=SelectSelectorMode.LIST, translation_key="component"
            )
        )
        translations = await self._translations()
        main = translations.get(f"component.{DOMAIN}.device.{profile.device_type}.name", profile.device_type)
        return self.async_show_form(
            step_id="components",
            data_schema=vol.Schema({vol.Required(CONF_COMPONENTS, default=default): selector}),
            description_placeholders={"model": profile.models[0], "main": main},
        )

    async def async_step_readings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        probe, connection = self._probe, self._connection
        if probe is None or connection is None:
            raise RuntimeError("readings step without a successful probe")
        selection = select(self._profile, self._components or [])
        readings = format_readings(
            self._profile, selection, probe, await self._translations(), self.hass.config.language
        )
        return self.async_show_menu(
            step_id="readings",
            menu_options=["name", "model", "connection"],
            description_placeholders={CONF_HOST: connection[CONF_HOST], "readings": readings},
        )

    async def async_step_name(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        profile = self._profile
        connection, probe = self._connection, self._probe
        if connection is None or probe is None:
            raise RuntimeError("name step without a connection")
        errors: dict[str, str] = {}
        device_id = free_device_id(self.hass, self.catalog, profile.device_type)
        placeholders: dict[str, str] = {}
        if user_input is not None:
            device_id = int(user_input[CONF_DEVICE_ID])
            serial = str(user_input.get(CONF_SERIAL_NUMBER) or "").strip()
            if device_id in used_device_ids(self.hass, self.catalog, profile.device_type):
                errors[CONF_DEVICE_ID] = "device_id_in_use"
            if serial and not valid_serial(serial):
                errors[CONF_SERIAL_NUMBER] = "invalid_serial_number"
            if not errors:
                # el escrito manda; si está vacío, el leído; si no hay ninguno, no se guarda
                serial = serial or probe.serial or ""
                data: dict[str, Any] = {
                    **connection,
                    CONF_PROFILE: profile.id,
                    CONF_COMPONENTS: [c.value for c in self._components or []],
                    CONF_INTERVALS: dict(DEFAULT_INTERVALS),
                    CONF_DEVICE_ID: device_id,
                }
                if serial:
                    data[CONF_SERIAL_NUMBER] = serial
                return self.async_create_entry(title=user_input[CONF_NAME], data=data)
        translations = await self._translations()
        selectors = await async_get_translations(self.hass, self.hass.config.language, "selector", {DOMAIN})
        device_name = translations.get(f"component.{DOMAIN}.device.{profile.device_type}.name", profile.device_type)
        if errors:
            placeholders = {"device_type": device_name.lower(), CONF_DEVICE_ID: str(device_id)}
        # ayuda del número de serie según el perfil y la lectura de la sonda
        if profile.serial is None:
            help_key = "none"
        elif probe.serial:
            help_key = "read"
        else:
            help_key = "unreadable"
        placeholders["serial_help"] = selectors.get(
            f"component.{DOMAIN}.selector.serial_help.options.{help_key}", help_key
        ).replace("{serial}", probe.serial or "")
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_DEVICE_ID): NumberSelector(
                    NumberSelectorConfig(min=0, step=1, mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_SERIAL_NUMBER): TextSelector(),
            }
        )
        suggested = user_input or {
            CONF_NAME: f"{BRAND_TITLES[profile.brand]} {profile.models[0]}",
            CONF_DEVICE_ID: device_id,
        }
        return self.async_show_form(
            step_id="name",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
            description_placeholders=placeholders,
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

    async def _probe_endpoint(self, host: str, port: int, unit_id: int, profile: DeviceProfile) -> ProbeResult:
        async with asyncio.timeout(PROBE_TIMEOUT_S):
            async with self.gateway_factory(self.hass, host, port, unit_id, profile) as gateway:
                return await probe_device(gateway, profile)
