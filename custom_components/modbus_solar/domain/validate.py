"""Comprobaciones estáticas de un perfil. Lista vacía = perfil válido."""

from itertools import combinations

from .control import GatedLimitSpec
from .encode import encode
from .errors import EncodeError
from .profile import DeviceProfile, RegisterSpec
from .types import WordOrder


def _overlaps(a: RegisterSpec, b: RegisterSpec) -> bool:
    # rangos [address, address + words) del mismo tipo de registro
    return a.kind is b.kind and a.address < b.address + b.dtype.words and b.address < a.address + a.dtype.words


def _control_problems(control: GatedLimitSpec, max_block_registers: int) -> list[str]:
    problems: list[str] = []
    name = control.key
    write = control.write
    if control.min_value > control.max_value:
        problems.append(f"{name}: min_value above max_value")
    if control.step <= 0:
        problems.append(f"{name}: step must be positive")
    if not control.min_value <= control.default <= control.max_value:
        problems.append(f"{name}: default out of range")
    if not control.min_value <= control.off_value <= control.max_value:
        problems.append(f"{name}: off_value out of range")
    if write.scale == 0:
        problems.append(f"{name}: write scale 0")
    if write.dtype.words != 1:
        problems.append(f"{name}: write dtype {write.dtype} is not 16-bit")
    # el valor va detrás del prefijo en la misma petición
    if len(write.prefix) + 1 > max_block_registers:
        problems.append(f"{name}: write longer than max_block_registers")
    if any(not 0 <= word <= 0xFFFF for word in write.prefix):
        problems.append(f"{name}: prefix word out of range")
    if write.scale != 0 and write.dtype.words == 1:
        # los extremos del rango y off_value son los valores que se escribirán
        for value in (control.min_value, control.max_value, control.off_value):
            try:
                encode(write, value)
            except EncodeError:
                problems.append(f"{name}: {value} does not encode")
    return problems


def validate_profile(profile: DeviceProfile) -> list[str]:
    problems: list[str] = []

    seen: set[str] = set()
    for spec in profile.entities:
        if spec.key in seen:
            problems.append(f"duplicate key: {spec.key}")
        seen.add(spec.key)
    if profile.probe_key not in seen:
        problems.append(f"probe_key missing: {profile.probe_key}")

    by_key = {spec.key: spec for spec in profile.entities}
    for energy in profile.energies:
        if energy.key in seen:
            problems.append(f"duplicate key: {energy.key}")
        seen.add(energy.key)
        sources = [by_key.get(key) for key in energy.sources]
        for key, source in zip(energy.sources, sources, strict=True):
            if source is None:
                problems.append(f"{energy.key}: unknown source {key}")
            elif source.device_class != "power":
                problems.append(f"{energy.key}: source {key} is not power")
        # el sensor de energía se suscribe a un solo coordinator
        if len({source.poll for source in sources if source is not None}) > 1:
            problems.append(f"{energy.key}: sources in different tiers")

    for control in profile.controls:
        for key in (control.key, control.switch_key):
            if key in seen:
                problems.append(f"duplicate key: {key}")
            seen.add(key)
        problems.extend(_control_problems(control, profile.max_block_registers))

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
