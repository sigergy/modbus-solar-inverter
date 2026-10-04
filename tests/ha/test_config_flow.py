"""Config flow de la entry de marca."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

# registra el handler en HANDLERS: supported_subentry_types lo busca ahí sin importar nada
import custom_components.modbus_solar.config_flow  # noqa: F401
from custom_components.modbus_solar.const import DOMAIN
from tests.ha.common import brand_entry


async def test_brand_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"brand": "ingeteam"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (result["title"], result["data"]) == ("Ingeteam", {"brand": "ingeteam"})
    assert result["result"].unique_id == "ingeteam"


async def test_brand_flow_aborts_if_brand_exists(hass: HomeAssistant) -> None:
    brand_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"brand": "ingeteam"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_brand_entry_offers_device_subentries(hass: HomeAssistant) -> None:
    entry = brand_entry()
    entry.add_to_hass(hass)
    assert entry.supported_subentry_types == {"device": {"supports_reconfigure": True}}
