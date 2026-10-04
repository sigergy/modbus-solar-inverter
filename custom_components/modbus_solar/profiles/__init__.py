"""Perfiles de equipo: solo importan domain."""

from ..domain.profile import DeviceProfile
from .ingeteam.oneplay_storage import ONEPLAY_STORAGE

ALL_PROFILES: tuple[DeviceProfile, ...] = (ONEPLAY_STORAGE,)
