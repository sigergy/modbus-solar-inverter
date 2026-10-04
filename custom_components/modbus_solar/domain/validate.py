"""Comprobaciones estáticas de un perfil. Lista vacía = perfil válido."""

from itertools import combinations

from .profile import DeviceProfile, RegisterSpec
from .types import WordOrder


def _overlaps(a: RegisterSpec, b: RegisterSpec) -> bool:
    # rangos [address, address + words) del mismo tipo de registro
    return a.kind is b.kind and a.address < b.address + b.dtype.words and b.address < a.address + a.dtype.words


def validate_profile(profile: DeviceProfile) -> list[str]:
    problems: list[str] = []

    seen: set[str] = set()
    for spec in profile.entities:
        if spec.key in seen:
            problems.append(f"duplicate key: {spec.key}")
        seen.add(spec.key)
    if profile.probe_key not in seen:
        problems.append(f"probe_key missing: {profile.probe_key}")

    for a, b in combinations(profile.entities, 2):
        if _overlaps(a.register, b.register):
            problems.append(f"overlap: {a.key} and {b.key}")

    for spec in profile.entities:
        reg = spec.register
        # HA exige options en un sensor enum: van juntos o no van
        if spec.enum is not None and spec.device_class != "enum":
            problems.append(f"{spec.key}: enum requires device_class enum")
        if spec.device_class == "enum" and spec.enum is None:
            problems.append(f"{spec.key}: device_class enum requires enum")
        if reg.scale == 0:
            problems.append(f"{spec.key}: scale 0")
        if reg.dtype.words == 1 and reg.word_order is not WordOrder.BIG:
            problems.append(f"{spec.key}: word_order {reg.word_order} on 16-bit type")
    return problems
