"""Catálogo de perfiles por marca e id. No conoce perfiles concretos: se los inyecta la raíz."""

from collections.abc import Iterable

from ..domain.profile import DeviceProfile


class Catalog:
    def __init__(self, profiles: Iterable[DeviceProfile]) -> None:
        self._by_id: dict[str, DeviceProfile] = {}
        for profile in profiles:
            if profile.id in self._by_id:
                raise ValueError(f"duplicate profile id: {profile.id}")
            self._by_id[profile.id] = profile

    def brands(self) -> list[str]:
        return sorted({p.brand for p in self._by_id.values()})

    def for_brand(self, brand: str) -> list[DeviceProfile]:
        return sorted((p for p in self._by_id.values() if p.brand == brand), key=lambda p: p.id)

    def get(self, profile_id: str) -> DeviceProfile:
        return self._by_id[profile_id]
