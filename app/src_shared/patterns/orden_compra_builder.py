"""Patron Builder (GoF) aplicado a la construccion de una orden de compra.

Antes, `ComponenteOrdenesCompra.emitirOrdenCompra` insertaba directamente
en `purchase_orders` sin validar que `items` no estuviera vacio: era
posible dejar creada una orden de compra con total 0 y sin ningun
producto asociado. `OrdenCompraBuilder` obliga a que la orden solo pueda
"salir" del builder cuando ya esta completa.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ItemOrdenCompraDTO:
    producto_id: int
    cantidad: int
    precio_acordado: float


@dataclass
class OrdenCompraDTO:
    proveedor_id: int
    items: list[ItemOrdenCompraDTO] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(i.cantidad * i.precio_acordado for i in self.items)


class OrdenCompraBuilder:
    """Estereotipo «Builder» del diagrama UML (OrdenCompraBuilder)."""

    def __init__(self) -> None:
        self._orden: OrdenCompraDTO | None = None

    def iniciar_orden(self, proveedor_id: int) -> "OrdenCompraBuilder":
        self._orden = OrdenCompraDTO(proveedor_id=proveedor_id)
        return self

    def agregar_item(
        self, producto_id: int, cantidad: int, precio: float
    ) -> "OrdenCompraBuilder":
        if self._orden is None:
            raise ValueError("Debe llamar iniciar_orden() antes de agregar items.")
        if cantidad <= 0:
            raise ValueError("La cantidad de un item debe ser mayor que cero.")
        self._orden.items.append(
            ItemOrdenCompraDTO(producto_id=producto_id, cantidad=cantidad, precio_acordado=precio)
        )
        return self

    def build(self) -> OrdenCompraDTO:
        if self._orden is None:
            raise ValueError("Debe llamar iniciar_orden() antes de construir la orden.")
        if not self._orden.items:
            raise ValueError("Una orden de compra debe tener al menos un item.")
        orden, self._orden = self._orden, None
        return orden
