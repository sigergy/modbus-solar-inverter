"""Perfiles de equipo: solo importan domain."""

from ..domain.profile import DeviceProfile
from .ingeteam.oneplay import ONEPLAY
from .ingeteam.oneplay_storage import ONEPLAY_STORAGE
from .mencke_tegtmeyer.si_rs485 import SI_RS485

ALL_PROFILES: tuple[DeviceProfile, ...] = (ONEPLAY, ONEPLAY_STORAGE, SI_RS485)
