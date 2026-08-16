"""Patron Proxy (GoF) sobre ComponenteVentas.

Antes, la verificacion de autorizacion vivia mezclada dentro de
`ComponenteVentas.crearPedido`: cualquiera que instanciara o extendiera
esa clase podia terminar registrando pedidos sin pasar por la validacion,
porque nada en el lenguaje obligaba a llamarla primero. `ProxyVentas`
implementa la misma interfaz que `ComponenteVentas` (IComponenteVentas) y
es la unica forma en que el resto de la aplicacion crea pedidos: primero
corre la cadena de autorizacion y solo si aprueba delega en el
componente real.
"""

from __future__ import annotations

import sqlite3
from typing import List, Sequence

from ..components import IComponenteVentas
from ..database import Database
from ..exceptions import EntidadNoEncontrada, VendedorNoAutorizado
from .validadores_autorizacion import ResultadoValidacion, construir_cadena_autorizacion


class ProxyVentas(IComponenteVentas):
    """Estereotipo «Proxy» del diagrama UML; `real` es el «Facade, RealSubject»."""

    def __init__(self, real: IComponenteVentas, db: Database, componente_rrhh) -> None:
        self._real = real
        self._db = db
        self._cadena = construir_cadena_autorizacion(componente_rrhh)

    def _validar_autorizacion(self, vendedor_id: int) -> None:
        vendedor: sqlite3.Row | None = self._db.conn.execute(
            "SELECT id, zona FROM employees WHERE id = ? AND is_seller = 1", (vendedor_id,)
        ).fetchone()
        if vendedor is None:
            raise EntidadNoEncontrada(f"Vendedor con ID={vendedor_id} no encontrado.")

        resultado = ResultadoValidacion()
        self._cadena.validar(vendedor, resultado)
        if not resultado.es_valido():
            raise VendedorNoAutorizado(resultado.motivo_rechazo)

    def crearPedido(
        self, cliente_id: int, vendedor_id: int, items: Sequence[tuple[int, int]]
    ) -> tuple[int, str]:
        self._validar_autorizacion(vendedor_id)
        return self._real.crearPedido(cliente_id, vendedor_id, items)

    def confirmarPedido(self, pedido_id: int) -> bool:
        return self._real.confirmarPedido(pedido_id)

    def cancelarPedido(self, pedido_id: int) -> None:
        self._real.cancelarPedido(pedido_id)

    def listarPedidosPorVendedor(self, vendedor_id: int) -> List[sqlite3.Row]:
        return self._real.listarPedidosPorVendedor(vendedor_id)
