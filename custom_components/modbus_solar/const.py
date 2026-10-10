"""Constantes de la integración y claves de configuración."""

DOMAIN = "modbus_solar"

CONF_PROFILE = "profile"
CONF_UNIT_ID = "unit_id"
CONF_INTERVALS = "intervals"
CONF_COMPONENTS = "components"
# modo de medición de red; ausente = el primero del perfil
CONF_METERING = "metering"
# seguimiento de costes de red; ausente = sin costes
CONF_COSTS = "costs"
CONF_DEVICE_ID = "device_id"
CONF_SERIAL_NUMBER = "serial_number"

# segundos por tier; editables en el reconfigure de cada equipo
DEFAULT_INTERVALS = {"instant": 5, "fast": 10, "normal": 60, "slow": 3600}

BRAND_TITLES = {"ingeteam": "Ingeteam", "mencke_tegtmeyer": "Ingenieurbüro Mencke & Tegtmeyer"}
