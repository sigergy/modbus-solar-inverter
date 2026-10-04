"""Constantes de la integración y claves de configuración."""

DOMAIN = "modbus_solar"

CONF_PROFILE = "profile"
CONF_UNIT_ID = "unit_id"
CONF_INTERVALS = "intervals"

# segundos por tier; editables en el reconfigure de cada equipo
DEFAULT_INTERVALS = {"instant": 5, "fast": 10, "normal": 60, "slow": 3600}

BRAND_TITLES = {"ingeteam": "Ingeteam", "mencke_tegtmeyer": "Ingenieurbüro Mencke & Tegtmeyer"}
