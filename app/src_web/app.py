from pathlib import Path
import sys

from flask import Flask, flash, g, redirect, render_template, request, url_for

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src_shared import crear_servicios


def _parse_items(raw_items: str) -> list[tuple[int, int]]:
    items: list[tuple[int, int]] = []
    for line in raw_items.splitlines():
        cleaned = line.strip()
        if cleaned == "":
            continue
        parts = cleaned.split(":")
        if len(parts) != 2:
            raise ValueError("Formato invalido. Use una linea por item: producto_id:cantidad")
        producto_id = int(parts[0].strip())
        cantidad = int(parts[1].strip())
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero.")
        items.append((producto_id, cantidad))
    if len(items) == 0:
        raise ValueError("Debe enviar al menos un item.")
    return items


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "polimarket-web-secret"

    def get_servicios():
        if "servicios" not in g:
            g.servicios = crear_servicios(PROJECT_ROOT / "polimarket.db")
        return g.servicios

    @app.teardown_appcontext
    def close_servicios(_error):
        servicios = g.pop("servicios", None)
        if servicios is not None:
            servicios.db.close()

    @app.get("/")
    def index():
        servicios = get_servicios()
        vendedores = servicios.componentes_rrhh.listarVendedoresActivos()
        clientes = servicios.componentes_clientes.listarClientes()
        productos = servicios.componentes_catalogo.listarProductos()
        ordenes_pendientes = servicios.componentes_ordenes.listarOrdenesPendientes()
        entregas_pendientes = servicios.componentes_entregas.listarEntregasPendientes()
        pedidos = list(
            servicios.db.conn.execute(
                """
                SELECT o.id, o.fecha, o.estado, o.total, c.nombre AS cliente, e.nombre AS vendedor
                FROM orders o
                JOIN clients c ON c.id = o.cliente_id
                JOIN employees e ON e.id = o.vendedor_id
                ORDER BY o.id DESC
                LIMIT 20
                """
            )
        )
        return render_template(
            "index.html",
            vendedores=vendedores,
            clientes=clientes,
            productos=productos,
            ordenes_pendientes=ordenes_pendientes,
            entregas_pendientes=entregas_pendientes,
            pedidos=pedidos,
        )

    @app.post("/rf1/autorizar")
    def autorizar_vendedor():
        servicios = get_servicios()
        vendedor_id = int(request.form["vendedor_id"])
        autorizado_por = int(request.form["autorizado_por"])
        servicios.componentes_rrhh.autorizarVendedor(vendedor_id, autorizado_por)
        flash("RF1 ejecutado: vendedor autorizado.", "success")
        return redirect(url_for("index"))

    @app.post("/rf2/crear-pedido")
    def crear_pedido():
        servicios = get_servicios()
        cliente_id = int(request.form["cliente_id"])
        vendedor_id = int(request.form["vendedor_id"])
        items = _parse_items(request.form["items"])
        pedido_id, estado = servicios.componentes_ventas.crearPedido(cliente_id, vendedor_id, items)
        if estado == "confirmado":
            flash(f"RF2 ejecutado: pedido #{pedido_id} confirmado.", "success")
        else:
            flash(
                f"RF2 ejecutado: pedido #{pedido_id} pendiente por falta de stock.",
                "warning",
            )
        return redirect(url_for("index"))

    @app.post("/rf3/verificar-stock")
    def verificar_stock():
        servicios = get_servicios()
        producto_id = int(request.form["producto_id"])
        cantidad = int(request.form["cantidad"])
        disponible = servicios.componentes_stock.verificarDisponibilidad(producto_id, cantidad)
        actual = servicios.componentes_stock.getStockActual(producto_id)
        estado = "SI" if disponible else "NO"
        flash(
            f"RF3 ejecutado: disponibilidad={estado}, stock actual={actual}.",
            "info",
        )
        return redirect(url_for("index"))

    @app.post("/rf4/recibir-orden")
    def recibir_orden():
        servicios = get_servicios()
        orden_id = int(request.form["orden_id"])
        items = list(
            servicios.db.conn.execute(
                "SELECT producto_id, cantidad FROM purchase_order_items WHERE orden_id = ?",
                (orden_id,),
            )
        )
        if len(items) == 0:
            raise ValueError("La orden no tiene items.")
        for item in items:
            servicios.componentes_movimientos.registrarEntrada(
                int(item["producto_id"]),
                int(item["cantidad"]),
                f"Recepcion orden de compra #{orden_id}",
            )
        servicios.componentes_ordenes.confirmarRecepcion(orden_id)
        flash(f"RF4 ejecutado: orden #{orden_id} recibida y stock repuesto.", "success")
        return redirect(url_for("index"))

    @app.post("/rf5/programar-entrega")
    def programar_entrega():
        servicios = get_servicios()
        pedido_id = int(request.form["pedido_id"])
        repartidor_id = int(request.form["repartidor_id"])
        fecha_programada = request.form["fecha_programada"]
        entrega_id = servicios.componentes_entregas.programarEntrega(
            pedido_id,
            repartidor_id,
            fecha_programada,
        )
        flash(f"RF5 ejecutado: entrega #{entrega_id} programada.", "success")
        return redirect(url_for("index"))

    @app.post("/rf5/confirmar-entrega")
    def confirmar_entrega():
        servicios = get_servicios()
        entrega_id = int(request.form["entrega_id"])
        servicios.componentes_entregas.confirmarEntrega(entrega_id)
        estado = servicios.componentes_entregas.getEstadoEntrega(entrega_id)
        flash(f"RF5 ejecutado: entrega #{entrega_id} confirmada. Estado={estado}.", "success")
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
