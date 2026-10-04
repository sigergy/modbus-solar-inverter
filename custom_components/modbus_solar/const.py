"""Constantes de la integración y claves de configuración."""

DOMAIN = "modbus_solar"

CONF_PROFILE = "profile"
CONF_UNIT_ID = "unit_id"
CONF_INTERVALS = "intervals"

# segundos por tier; editables en el reconfigure de cada equipo
DEFAULT_INTERVALS = {"fast": 5, "normal": 60, "slow": 3600}

BRAND_TITLES = {"ingeteam": "Ingeteam"}
