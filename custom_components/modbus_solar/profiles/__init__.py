"""Perfiles de equipo: solo importan domain."""

from ..domain.profile import DeviceProfile
from .ingeteam.oneplay import ONEPLAY

ALL_PROFILES: tuple[DeviceProfile, ...] = (ONEPLAY,)
