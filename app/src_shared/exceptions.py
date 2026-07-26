class PoliMarketError(Exception):
    """Base de todas las excepciones de negocio de PoliMarket."""


class EntidadNoEncontrada(PoliMarketError):
    """La entidad solicitada no existe en la base de datos."""


class VendedorNoAutorizado(PoliMarketError):
    """El vendedor no tiene autorizacion activa de RRHH."""


class ReglaDeNegocio(PoliMarketError):
    """Se violo una regla de negocio (estado incorrecto, stock insuficiente, etc.)."""
