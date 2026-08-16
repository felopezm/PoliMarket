"""Pruebas de los patrones GoF incorporados al diseno de PoliMarket.

Ejecutar desde app/: `pytest tests/test_patrones_gof.py -v`
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src_shared.bootstrap import crear_servicios
from src_shared.exceptions import ReglaDeNegocio, VendedorNoAutorizado
from src_shared.patterns.estados import (
    PedidoCancelado,
    PedidoConfirmado,
    PedidoCreado,
    PedidoEntregado,
    estado_desde_texto,
)
from src_shared.patterns.orden_compra_builder import OrdenCompraBuilder
from src_shared.patterns.precio_strategy import (
    PrecioDescuentoClienteStrategy,
    PrecioPromocionStrategy,
    PrecioRegularStrategy,
    resolver_estrategia,
)
from src_shared.patterns.stock_observer import IStockObserver, StockSubject
from src_shared.patterns.validadores_autorizacion import (
    ResultadoValidacion,
    ValidadorRRHH,
    ValidadorZonaAsignada,
    construir_cadena_autorizacion,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def servicios():
    tmp_path = Path(tempfile.mktemp(suffix=".db"))
    svc = crear_servicios(tmp_path)
    yield svc
    svc.db.close()
    tmp_path.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
def test_state_pedido_creado_puede_confirmarse():
    estado = PedidoCreado()
    siguiente = estado.confirmar()
    assert siguiente.nombre == "confirmado"


def test_state_no_se_puede_cancelar_pedido_entregado():
    estado = PedidoEntregado()
    with pytest.raises(ReglaDeNegocio):
        estado.cancelar()


def test_state_no_se_puede_confirmar_dos_veces():
    estado = PedidoConfirmado()
    with pytest.raises(ReglaDeNegocio):
        estado.confirmar()


def test_state_factory_reconstruye_desde_texto():
    assert isinstance(estado_desde_texto("cancelado"), PedidoCancelado)
    with pytest.raises(ReglaDeNegocio):
        estado_desde_texto("estado_que_no_existe")


def test_state_integrado_bloquea_cancelar_pedido_entregado(servicios):
    """Reproduce el bug real que existia antes: cancelarPedido no validaba estado."""
    svc = servicios
    svc.componentes_rrhh.autorizarVendedor(2, 1)
    pedido_id, _ = svc.componentes_ventas.crearPedido(1, 2, [(1, 1)])
    svc.db.conn.execute("UPDATE orders SET estado = 'entregado' WHERE id = ?", (pedido_id,))
    svc.db.conn.commit()
    with pytest.raises(ReglaDeNegocio):
        svc.componentes_ventas.cancelarPedido(pedido_id)


# --------------------------------------------------------------------------- #
# Strategy
# --------------------------------------------------------------------------- #
def test_strategy_precio_regular():
    estrategia = PrecioRegularStrategy()
    assert estrategia.calcular(precio_base=100.0, cantidad=3) == 300.0


def test_strategy_descuento_cliente():
    estrategia = PrecioDescuentoClienteStrategy(porcentaje=10)
    assert estrategia.calcular(precio_base=100.0, cantidad=2) == 180.0


def test_strategy_promocion():
    estrategia = PrecioPromocionStrategy(codigo_promo="BLACKFRIDAY", porcentaje=20)
    assert estrategia.calcular(precio_base=50.0, cantidad=2) == 80.0


def test_strategy_resolver_prioriza_codigo_promo():
    estrategia = resolver_estrategia(total_pedidos_previos=0, codigo_promo="X")
    assert isinstance(estrategia, PrecioPromocionStrategy)


def test_strategy_resolver_cliente_frecuente():
    estrategia = resolver_estrategia(total_pedidos_previos=5, codigo_promo=None)
    assert isinstance(estrategia, PrecioDescuentoClienteStrategy)


# --------------------------------------------------------------------------- #
# Chain of Responsibility
# --------------------------------------------------------------------------- #
def test_chain_rechaza_vendedor_sin_zona():
    class FakeRRHH:
        def verificarAutorizacion(self, vendedor_id):
            return True

    cadena = construir_cadena_autorizacion(FakeRRHH())
    resultado = ResultadoValidacion()
    vendedor = {"id": 1, "zona": None}
    cadena.validar(vendedor, resultado)
    assert resultado.es_valido() is False
    assert "zona" in resultado.motivo_rechazo.lower()


def test_chain_aprueba_cuando_todos_los_validadores_pasan():
    class FakeRRHH:
        def verificarAutorizacion(self, vendedor_id):
            return True

    cadena = construir_cadena_autorizacion(FakeRRHH())
    resultado = ResultadoValidacion()
    vendedor = {"id": 1, "zona": "Sur"}
    cadena.validar(vendedor, resultado)
    assert resultado.es_valido() is True


def test_chain_integrada_con_proxy_reales(servicios):
    svc = servicios
    with pytest.raises(VendedorNoAutorizado):
        svc.componentes_ventas.crearPedido(1, 2, [(1, 1)])


# --------------------------------------------------------------------------- #
# Proxy
# --------------------------------------------------------------------------- #
def test_proxy_delega_en_ventas_core_cuando_autoriza(servicios):
    svc = servicios
    svc.componentes_rrhh.autorizarVendedor(2, 1)
    pedido_id, estado = svc.componentes_ventas.crearPedido(1, 2, [(1, 1)])
    assert estado == "confirmado"
    assert pedido_id > 0


# --------------------------------------------------------------------------- #
# Builder
# --------------------------------------------------------------------------- #
def test_builder_rechaza_orden_sin_items():
    with pytest.raises(ValueError):
        OrdenCompraBuilder().iniciar_orden(1).build()


def test_builder_construye_orden_completa():
    orden = (
        OrdenCompraBuilder()
        .iniciar_orden(1)
        .agregar_item(producto_id=10, cantidad=5, precio=20.0)
        .build()
    )
    assert orden.total == 100.0
    assert len(orden.items) == 1


def test_builder_integrado_rechaza_orden_vacia(servicios):
    with pytest.raises(ValueError):
        servicios.componentes_ordenes.emitirOrdenCompra(1, [])


# --------------------------------------------------------------------------- #
# Observer
# --------------------------------------------------------------------------- #
def test_observer_notifica_a_todos_los_suscriptores():
    eventos = []

    class ObservadorDePrueba(IStockObserver):
        def actualizar(self, producto_id, cantidad_disponible, cantidad_minima):
            eventos.append((producto_id, cantidad_disponible, cantidad_minima))

    subject = StockSubject()
    subject.suscribir(ObservadorDePrueba())
    subject.notificar(producto_id=1, cantidad_disponible=1, cantidad_minima=5)
    assert eventos == [(1, 1, 5)]


def test_observer_integrado_genera_orden_al_confirmar_pedido(servicios):
    svc = servicios
    svc.componentes_rrhh.autorizarVendedor(2, 1)
    # producto 2 (Mouse) tiene stock=2 y minima=3 en la semilla
    svc.componentes_ventas.crearPedido(1, 2, [(2, 1)])
    ordenes = svc.componentes_ordenes.listarOrdenesPendientes()
    assert len(ordenes) == 1
