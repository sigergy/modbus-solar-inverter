"""Modbus Solar: raíz de composición."""

from .application.catalog import Catalog
from .profiles import ALL_PROFILES

CATALOG = Catalog(ALL_PROFILES)
