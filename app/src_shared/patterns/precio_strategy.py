"""Patron Strategy (GoF) aplicado al calculo del precio de un item de pedido.

Antes, `getPrecio` en ComponenteCatalogo devolvia siempre el precio de
lista, sin posibilidad de aplicar descuentos por cliente frecuente o
promociones sin tocar ComponenteVentas. Aqui el calculo se delega en una
implementacion intercambiable de IPrecioStrategy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class IPrecioStrategy(ABC):
    """Interfaz de estrategia de precio del diagrama UML (IPrecioStrategy)."""

    @abstractmethod
    def calcular(self, precio_base: float, cantidad: int) -> float:
        """Devuelve el subtotal para `cantidad` unidades a partir del precio de lista."""


class PrecioRegularStrategy(IPrecioStrategy):
    def calcular(self, precio_base: float, cantidad: int) -> float:
        return precio_base * cantidad


class PrecioDescuentoClienteStrategy(IPrecioStrategy):
    """Aplica un descuento fijo, pensado para clientes con historial de compras."""

    def __init__(self, porcentaje: float) -> None:
        if not 0 <= porcentaje <= 100:
            raise ValueError("El porcentaje de descuento debe estar entre 0 y 100.")
        self.porcentaje = porcentaje

    def calcular(self, precio_base: float, cantidad: int) -> float:
        subtotal = precio_base * cantidad
        return subtotal * (1 - self.porcentaje / 100)


class PrecioPromocionStrategy(IPrecioStrategy):
    """Aplica el descuento asociado a un codigo de promocion activo."""

    def __init__(self, codigo_promo: str, porcentaje: float) -> None:
        self.codigo_promo = codigo_promo
        if not 0 <= porcentaje <= 100:
            raise ValueError("El porcentaje de la promocion debe estar entre 0 y 100.")
        self.porcentaje = porcentaje

    def calcular(self, precio_base: float, cantidad: int) -> float:
        subtotal = precio_base * cantidad
        return subtotal * (1 - self.porcentaje / 100)


HISTORIAL_MINIMO_DESCUENTO = 3
PORCENTAJE_DESCUENTO_CLIENTE_FRECUENTE = 5.0


def resolver_estrategia(
    total_pedidos_previos: int, codigo_promo: str | None
) -> IPrecioStrategy:
    """Elige la estrategia de precio segun el codigo de promocion y el historial
    del cliente. Codigo de promocion tiene prioridad sobre el descuento por
    cliente frecuente; si no aplica ninguno, se usa el precio regular.
    """
    if codigo_promo:
        return PrecioPromocionStrategy(codigo_promo, porcentaje=10.0)
    if total_pedidos_previos >= HISTORIAL_MINIMO_DESCUENTO:
        return PrecioDescuentoClienteStrategy(PORCENTAJE_DESCUENTO_CLIENTE_FRECUENTE)
    return PrecioRegularStrategy()
