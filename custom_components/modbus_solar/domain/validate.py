"""Comprobaciones estáticas de un perfil. Lista vacía = perfil válido."""

from itertools import combinations

from .control import GatedLimitSpec
from .encode import encode
from .energy import SignFilter
from .errors import EncodeError
from .profile import DeviceProfile, RegisterSpec
from .types import Component, DataType, Platform, Role, WordOrder


def _overlaps(a: RegisterSpec, b: RegisterSpec) -> bool:
    # rangos [address, address + words) del mismo tipo de registro
    return a.kind is b.kind and a.address < b.address + b.words and b.address < a.address + a.words


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


def _component_problems(profile: DeviceProfile) -> list[str]:
    problems: list[str] = []
    declared: set[Component] = set()
    for spec in profile.components:
        if spec.component is Component.MAIN:
            problems.append("components: main is implicit")
        elif spec.component in declared:
            problems.append(f"components: {spec.component} repeated")
        declared.add(spec.component)
    # entidades, energías y controles cuentan para «componente no vacío»
    members = [(item.key, item.component) for item in (*profile.entities, *profile.energies, *profile.controls)]
    used = {component for _, component in members}
    for key, component in members:
        if component is not Component.MAIN and component not in declared:
            problems.append(f"{key}: component {component} not declared")
    for spec in profile.components:
        if spec.component is not Component.MAIN and spec.component not in used:
            problems.append(f"components: {spec.component} is empty")
    return problems


def _metering_problems(profile: DeviceProfile, seen: set[str]) -> list[str]:
    """Modos de medición: clave única, fuente de potencia leída y claves de flujo sin choques."""
    problems: list[str] = []
    by_key = {spec.key: spec for spec in profile.entities}
    modes: set[str] = set()
    # una clave puede repetirse entre modos (mismo unique_id): con el mismo rol y signo
    flow_keys: dict[str, tuple[Role, SignFilter]] = {}
    for mode in profile.metering_modes:
        if mode.key in modes:
            problems.append(f"metering: {mode.key} repeated")
        modes.add(mode.key)
        if not mode.flows:
            problems.append(f"metering {mode.key}: no flows")
        source = by_key.get(mode.source)
        if source is None:
            problems.append(f"metering {mode.key}: unknown source {mode.source}")
        elif source.device_class != "power":
            problems.append(f"metering {mode.key}: source {mode.source} is not power")
        mode_keys: set[str] = set()
        for flow in mode.flows:
            if (flow.cost_key is None) != (flow.cost_role is None):
                problems.append(f"metering {mode.key}: cost_key and cost_role go together")
            keys = [(flow.power_key, flow.power_role), (flow.energy_key, flow.energy_role)]
            if flow.cost_key is not None and flow.cost_role is not None:
                keys.append((flow.cost_key, flow.cost_role))
            for key, role in keys:
                if key in seen or key in mode_keys:
                    problems.append(f"duplicate key: {key}")
                mode_keys.add(key)
                if flow_keys.setdefault(key, (role, flow.sign)) != (role, flow.sign):
                    problems.append(f"metering: {key} differs between modes")
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
        # una energía del perfil vive en el componente de sus fuentes (las de un modo, en el del modo)
        if any(source is not None and source.component is not energy.component for source in sources):
            problems.append(f"{energy.key}: component differs from sources")
        # el sensor de energía se suscribe a un solo coordinator
        if len({source.poll for source in sources if source is not None}) > 1:
            problems.append(f"{energy.key}: sources in different tiers")

    for control in profile.controls:
        for key in (control.key, control.switch_key):
            if key in seen:
                problems.append(f"duplicate key: {key}")
            seen.add(key)
        problems.extend(_control_problems(control, profile.max_block_registers))

    problems.extend(_metering_problems(profile, seen))
    problems.extend(_component_problems(profile))

    for a, b in combinations(profile.entities, 2):
        # dos bits del mismo registro no se solapan
        if a.bit is not None and b.bit is not None:
            continue
        if _overlaps(a.register, b.register):
            problems.append(f"overlap: {a.key} and {b.key}")

    for spec in profile.entities:
        reg = spec.register
        # HA exige options en un sensor enum: van juntos o no van
        if spec.enum is not None and spec.device_class != "enum":
            problems.append(f"{spec.key}: enum requires device_class enum")
        if spec.device_class == "enum" and spec.enum is None:
            problems.append(f"{spec.key}: device_class enum requires enum")
        if reg.dtype is DataType.ASCII:
            problems.append(f"{spec.key}: ascii only for serial")
            continue
        if spec.bit is not None:
            if spec.platform is not Platform.BINARY_SENSOR:
                problems.append(f"{spec.key}: bit requires binary_sensor")
            elif reg.dtype is not DataType.U16:
                problems.append(f"{spec.key}: bit requires u16")
            elif not 0 <= spec.bit <= 15:
                problems.append(f"{spec.key}: bit out of range")
        elif spec.platform is Platform.BINARY_SENSOR:
            problems.append(f"{spec.key}: binary_sensor requires bit")
        if reg.scale == 0:
            problems.append(f"{spec.key}: scale 0")
        if reg.dtype is not DataType.ASCII and reg.words == 1 and reg.word_order is not WordOrder.BIG:
            problems.append(f"{spec.key}: word_order {reg.word_order} on 16-bit type")
    if profile.serial is not None:
        if profile.serial.dtype is not DataType.ASCII:
            problems.append("serial: dtype must be ascii")
        elif profile.serial.length < 1:
            problems.append("serial: length must be >= 1")
    return problems
