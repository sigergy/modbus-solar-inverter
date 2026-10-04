"""Errores del dominio. Solo el gateway conoce las excepciones de modbus_connection."""


class DeviceUnavailable(Exception):
    """El equipo no responde: sin conexión o tiempo agotado."""


class DeviceProtocolError(Exception):
    """El equipo responde con una excepción Modbus o una trama inválida."""


class DecodeError(Exception):
    """Las palabras leídas no dan un valor válido para la entidad."""


class EncodeError(Exception):
    """El valor no cabe en el tipo de la escritura."""


class EndpointInUse(Exception):
    """El endpoint ya está abierto con otros parámetros de enlace."""
