"""Un DataUpdateCoordinator por tier de sondeo de un equipo."""

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from ...application.poller import TierResult, read_tier
from ...domain.errors import DeviceProtocolError, DeviceUnavailable
from ...domain.profile import DeviceProfile
from ...domain.types import PollTier
from ...ports.device import DeviceGateway

_LOGGER = logging.getLogger(__name__)


class TierCoordinator(DataUpdateCoordinator[TierResult]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        name: str,
        tier: PollTier,
        interval_s: int,
        gateway: DeviceGateway,
        profile: DeviceProfile,
        keys: Iterable[str],
        always_update: bool = False,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=name,
            update_interval=timedelta(seconds=interval_s),
            # HA solo escribe estado si el TierResult cambia; los tiers con fuentes de
            # energía avisan en cada lectura para que la integral avance con potencia constante
            always_update=always_update,
        )
        self.tier = tier
        self.keys = frozenset(keys)
        self.last_error: str | None = None
        self.last_error_at: datetime | None = None
        self._gateway = gateway
        self._profile = profile
        self._warned: set[str] = set()

    async def _async_update_data(self) -> TierResult:
        try:
            result = await read_tier(self.tier, self._gateway, self._profile, self.keys)
        except (DeviceUnavailable, DeviceProtocolError) as err:
            self.last_error = f"{type(err).__name__}: {err}"
            self.last_error_at = dt_util.utcnow()
            # DataUpdateCoordinator registra un error al perder el equipo y un info al recuperarlo
            raise UpdateFailed(str(err)) from err
        for key, message in result.decode_errors.items():
            if key not in self._warned:
                _LOGGER.warning("%s: %s", self.name, message)
        # una clave que vuelve a decodificar bien puede volver a avisar
        self._warned = set(result.decode_errors)
        return result
