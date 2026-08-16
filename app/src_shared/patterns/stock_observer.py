"""Patron Observer (GoF) aplicado a la notificacion de stock bajo.

Antes, `ComponenteStock.verificarDisponibilidad` llamaba directamente a
`self.componente_ordenes.emitirOrdenCompraPorProducto(...)`: Bodega
conocia y dependia en firme del componente concreto de Proveedores. Con
Observer, Bodega (el «Subject») solo conoce la interfaz IStockObserver;
Proveedores se suscribe sin que Bodega sepa que existe.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class IStockObserver(ABC):
    @abstractmethod
    def actualizar(self, producto_id: int, cantidad_disponible: int, cantidad_minima: int) -> None:
        ...


class StockSubject:
    """Mixin del rol «Subject» que puede usar cualquier componente de stock."""

    def __init__(self) -> None:
        self._observadores: List[IStockObserver] = []

    def suscribir(self, observador: IStockObserver) -> None:
        self._observadores.append(observador)

    def desuscribir(self, observador: IStockObserver) -> None:
        self._observadores.remove(observador)

    def notificar(self, producto_id: int, cantidad_disponible: int, cantidad_minima: int) -> None:
        for observador in list(self._observadores):
            observador.actualizar(producto_id, cantidad_disponible, cantidad_minima)


class NotificadorOrdenesCompra(IStockObserver):
    """Adaptador que implementa IStockObserver delegando en
    ComponenteOrdenesCompra (rol FachadaProveedores del diagrama)."""

    def __init__(self, componente_ordenes) -> None:
        self._componente_ordenes = componente_ordenes

    def actualizar(self, producto_id: int, cantidad_disponible: int, cantidad_minima: int) -> None:
        sugerida = max((cantidad_minima * 2) - cantidad_disponible, cantidad_minima)
        self._componente_ordenes.emitirOrdenCompraPorProducto(producto_id, int(sugerida))
