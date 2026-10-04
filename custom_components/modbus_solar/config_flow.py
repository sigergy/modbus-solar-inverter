"""Config flow: compone el flow de adapters/inbound con el catálogo y el gateway Modbus."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusTcpParams

from . import CATALOG
from .adapters.inbound.flow import DeviceConfigFlow
from .adapters.outbound.modbus_gateway import ModbusGateway
from .const import DOMAIN
from .domain.errors import EndpointInUse
from .domain.profile import DeviceProfile
from .ports.device import DeviceGateway


@asynccontextmanager
async def open_gateway(
    hass: HomeAssistant, host: str, port: int, unit_id: int, profile: DeviceProfile
) -> AsyncIterator[DeviceGateway]:
    # unit temporal: se cierra al salir si ninguna entry comparte la conexión
    async with AsyncExitStack() as stack:
        try:
            unit = await stack.enter_async_context(
                async_get_temporary_unit(hass, ModbusTcpParams(host=host, port=port), unit_id)
            )
        except HomeAssistantError as err:
            # solo la apertura: endpoint en uso con otros parámetros de enlace
            raise EndpointInUse(str(err)) from err
        yield ModbusGateway(unit, profile)


class ModbusSolarConfigFlow(DeviceConfigFlow, domain=DOMAIN):
    catalog = CATALOG
    gateway_factory = staticmethod(open_gateway)
