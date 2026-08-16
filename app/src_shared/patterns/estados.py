"""Patron State (GoF) aplicado al ciclo de vida de Pedido.

Antes de este cambio, `estado` en `orders` era un simple string y
`ComponenteVentas.cancelarPedido` no verificaba en que estado estaba el
pedido antes de cancelarlo: un pedido con estado 'entregado' podia
cancelarse igual. Este modulo mueve esa regla a clases de estado, cada
una responsable de decidir que transiciones son validas desde si misma.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..exceptions import ReglaDeNegocio


class IEstadoPedido(ABC):
    """Interfaz de estado del diagrama UML (IEstadoPedido)."""

    nombre: str

    @abstractmethod
    def confirmar(self) -> "IEstadoPedido":
        """Devuelve el siguiente estado o lanza ReglaDeNegocio si no aplica."""

    @abstractmethod
    def cancelar(self) -> "IEstadoPedido":
        """Devuelve el siguiente estado o lanza ReglaDeNegocio si no aplica."""


class PedidoCreado(IEstadoPedido):
    nombre = "creado"

    def confirmar(self) -> IEstadoPedido:
        return PedidoConfirmado()

    def cancelar(self) -> IEstadoPedido:
        return PedidoCancelado()


class PedidoPendienteSinStock(IEstadoPedido):
    nombre = "pendiente_sin_stock"

    def confirmar(self) -> IEstadoPedido:
        return PedidoConfirmado()

    def cancelar(self) -> IEstadoPedido:
        return PedidoCancelado()


class PedidoConfirmado(IEstadoPedido):
    nombre = "confirmado"

    def confirmar(self) -> IEstadoPedido:
        raise ReglaDeNegocio("El pedido ya fue confirmado.")

    def cancelar(self) -> IEstadoPedido:
        return PedidoCancelado()


class PedidoEnEntrega(IEstadoPedido):
    nombre = "en_entrega"

    def confirmar(self) -> IEstadoPedido:
        raise ReglaDeNegocio("El pedido ya esta en proceso de entrega.")

    def cancelar(self) -> IEstadoPedido:
        raise ReglaDeNegocio(
            "No se puede cancelar un pedido que ya esta en proceso de entrega."
        )


class PedidoEntregado(IEstadoPedido):
    nombre = "entregado"

    def confirmar(self) -> IEstadoPedido:
        raise ReglaDeNegocio("El pedido ya fue entregado.")

    def cancelar(self) -> IEstadoPedido:
        raise ReglaDeNegocio("No se puede cancelar un pedido ya entregado.")


class PedidoCancelado(IEstadoPedido):
    nombre = "cancelado"

    def confirmar(self) -> IEstadoPedido:
        raise ReglaDeNegocio("No se puede confirmar un pedido cancelado.")

    def cancelar(self) -> IEstadoPedido:
        raise ReglaDeNegocio("El pedido ya esta cancelado.")


_ESTADOS: dict[str, type[IEstadoPedido]] = {
    "creado": PedidoCreado,
    "pendiente_sin_stock": PedidoPendienteSinStock,
    "confirmado": PedidoConfirmado,
    "en_entrega": PedidoEnEntrega,
    "entregado": PedidoEntregado,
    "cancelado": PedidoCancelado,
}


def estado_desde_texto(valor: str) -> IEstadoPedido:
    """Factory: reconstruye el objeto de estado a partir de la columna 'estado'."""
    clase = _ESTADOS.get(valor)
    if clase is None:
        raise ReglaDeNegocio(f"Estado de pedido desconocido: '{valor}'.")
    return clase()
