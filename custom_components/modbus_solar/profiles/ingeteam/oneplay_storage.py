"""Ingeteam 1Play Storage. Fuente: PDF ACL2010IMB05 (docs/wiki/brands/ingeteam/1-play-tl-m/)."""

from ...domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from ...domain.types import DataType, Platform, PollTier, Role

ONEPLAY_STORAGE = DeviceProfile(
    id="ingeteam.oneplay_storage",
    brand="ingeteam",
    device_type="inverter",
    models=("1Play Storage",),
    # pág. 4: periodo entre peticiones >= 1 s y de 1 a 124 registros por lectura (FC03)
    min_request_interval_s=1.0,
    max_block_registers=124,
    default_port=502,
    default_unit_id=1,
    probe_key="inverter_state",
    entities=(
        EntitySpec(
            key="inverter_state",
            role=Role.INVERTER_STATE,
            platform=Platform.SENSOR,
            register=RegisterSpec(address=0x101D, dtype=DataType.U16),
            poll=PollTier.FAST,
            device_class="enum",
            # Nota 3 (pág. 7): solo estos tres estados están documentados
            enum={0: "factory_default", 1: "grid_disconnected", 3: "grid_connected"},
        ),
        EntitySpec(
            key="active_power",
            role=Role.AC_POWER,
            platform=Platform.SENSOR,
            # [W x 10] según el PDF: scale 0.1 sin verificar en equipo; se comprueba con diagnostics
            register=RegisterSpec(address=0x1037, dtype=DataType.S32, scale=0.1),
            poll=PollTier.FAST,
            device_class="power",
            state_class="measurement",
            unit="W",
        ),
        EntitySpec(
            key="total_energy",
            role=Role.ENERGY_PRODUCED_TOTAL,
            platform=Platform.SENSOR,
            # [Wh x 10] según el PDF: scale 0.1 sin verificar en equipo; se comprueba con diagnostics
            register=RegisterSpec(address=0x1021, dtype=DataType.U32, scale=0.1),
            poll=PollTier.NORMAL,
            device_class="energy",
            state_class="total_increasing",
            unit="Wh",
        ),
    ),
)
