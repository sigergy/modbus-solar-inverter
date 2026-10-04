"""Sensor de irradiancia Si-RS485TC-…-MB. Fuente: Specification_Si-RS485_MODBUS.pdf
(docs/wiki/brands/mencke-tegtmeyer/si-rs485-mb/)."""

from ...domain.profile import DeviceProfile, EntitySpec, RegisterSpec
from ...domain.types import DataType, Platform, PollTier, RegisterKind, Role

SI_RS485 = DeviceProfile(
    id="mencke_tegtmeyer.si_rs485",
    brand="mencke_tegtmeyer",
    device_type="irradiance_sensor",
    models=("Si-RS485TC-T-MB", "Si-RS485TC-2T-MB", "Si-RS485TC-2T-v-MB", "Si-RS485TC-T-Tm-MB"),
    # el PDF no fija un mínimo entre peticiones: 1 s como en Ingeteam (supuesto)
    min_request_interval_s=1.0,
    # los registros 0, 3, 7 y 8 quedan a huecos de hasta 3: un solo bloque de 9 registros; los
    # huecos existen y se leen sin error (págs. 1-2)
    max_gap=3,
    # pág. 1: dirección 1 de fábrica; el puerto es el de la pasarela RS485 → Modbus TCP
    default_port=502,
    default_unit_id=1,
    probe_key="irradiance",
    entities=(
        EntitySpec(
            key="irradiance",
            role=Role.IRRADIANCE,
            platform=Platform.SENSOR,
            # pág. 1: registro 0000, UINT16, ganancia 0.1, 0…1500 W/m²
            register=RegisterSpec(address=0, kind=RegisterKind.INPUT, dtype=DataType.U16, scale=0.1),
            poll=PollTier.FAST,
            device_class="irradiance",
            state_class="measurement",
            unit="W/m²",
        ),
        EntitySpec(
            key="wind_speed",
            role=Role.WIND_SPEED,
            platform=Platform.SENSOR,
            # pág. 1: registro 0003, UINT16, ganancia 0.1; opcional: sin sensor devuelve 0
            register=RegisterSpec(address=3, kind=RegisterKind.INPUT, dtype=DataType.U16, scale=0.1),
            poll=PollTier.FAST,
            device_class="wind_speed",
            state_class="measurement",
            unit="m/s",
        ),
        EntitySpec(
            key="cell_temperature",
            role=Role.CELL_TEMPERATURE,
            platform=Platform.SENSOR,
            # pág. 1: registro 0007, INT16, ganancia 0.1; exige firmware >= 1.53
            register=RegisterSpec(address=7, kind=RegisterKind.INPUT, dtype=DataType.S16, scale=0.1),
            poll=PollTier.FAST,
            device_class="temperature",
            state_class="measurement",
            unit="°C",
        ),
        EntitySpec(
            key="external_temperature",
            role=Role.EXTERNAL_TEMPERATURE,
            platform=Platform.SENSOR,
            # pág. 1: registro 0008 (temperatura externa 1), INT16, ganancia 0.1; firmware >= 1.53;
            # opcional. Según el modelo mide el ambiente o el módulo (pág. 5)
            register=RegisterSpec(address=8, kind=RegisterKind.INPUT, dtype=DataType.S16, scale=0.1),
            poll=PollTier.FAST,
            device_class="temperature",
            state_class="measurement",
            unit="°C",
        ),
    ),
)
