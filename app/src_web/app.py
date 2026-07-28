from pathlib import Path
import sys

from flask import Flask, flash, g, redirect, render_template, request, url_for
import json
import queue
from threading import Thread
from time import sleep

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src_shared import crear_servicios
from src_shared.exceptions import PoliMarketError


def _parse_items_form() -> list[tuple[int, int]]:
    """Lee item_producto[] e item_cantidad[] del formulario RF2."""
    productos = request.form.getlist("item_producto")
    cantidades = request.form.getlist("item_cantidad")
    items: list[tuple[int, int]] = []
    for pid, qty in zip(productos, cantidades):
        pid = pid.strip()
        qty = qty.strip()
        if not pid or not qty:
            continue
        cantidad = int(qty)
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero.")
        items.append((int(pid), cantidad))
    if not items:
        raise ValueError("Debe agregar al menos un producto al pedido.")
    return items


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "polimarket-web-secret"
    # Simple in-memory broadcaster for Server-Sent Events (SSE)
    app.broadcaster = []  # list of queue.Queue()

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
        active_tab = request.args.get("tab", "tab-rf1")

        vendedores = servicios.componentes_rrhh.listarVendedoresActivos()
        clientes = servicios.componentes_clientes.listarClientes()
        productos = servicios.componentes_catalogo.listarProductos()
        ordenes_pendientes = servicios.componentes_ordenes.listarOrdenesPendientes()
        entregas_pendientes = servicios.componentes_entregas.listarEntregasPendientes()

        empleados_rrhh = list(servicios.db.conn.execute(
            "SELECT id, nombre, cargo FROM employees WHERE estado = 'activo' AND cargo = 'RRHH' ORDER BY nombre"
        ))
        repartidores = list(servicios.db.conn.execute(
            "SELECT id, nombre FROM employees WHERE estado = 'activo' AND cargo = 'Repartidor' ORDER BY nombre"
        ))
        pedidos_confirmados = list(servicios.db.conn.execute(
            """
            SELECT o.id, c.nombre AS cliente, o.total
            FROM orders o
            JOIN clients c ON c.id = o.cliente_id
            WHERE o.estado = 'confirmado'
            ORDER BY o.id DESC
            """
        ))
        stock_actual = {
            row["product_id"]: row["cantidad_disponible"]
            for row in servicios.db.conn.execute("SELECT product_id, cantidad_disponible FROM stock")
        }
        pedidos = list(servicios.db.conn.execute(
            """
            SELECT o.id, o.fecha, o.estado, o.total, c.nombre AS cliente, e.nombre AS vendedor
            FROM orders o
            JOIN clients c ON c.id = o.cliente_id
            JOIN employees e ON e.id = o.vendedor_id
            ORDER BY o.id DESC
            LIMIT 30
            """
        ))
        return render_template(
            "index.html",
            active_tab=active_tab,
            vendedores=vendedores,
            clientes=clientes,
            productos=productos,
            ordenes_pendientes=ordenes_pendientes,
            entregas_pendientes=entregas_pendientes,
            empleados_rrhh=empleados_rrhh,
            repartidores=repartidores,
            pedidos_confirmados=pedidos_confirmados,
            stock_actual=stock_actual,
            pedidos=pedidos,
        )

    @app.post("/rf1/autorizar")
    def autorizar_vendedor():
        active_tab = request.form.get("active_tab", "tab-rf1")
        try:
            servicios = get_servicios()
            vendedor_id = int(request.form["vendedor_id"])
            autorizado_por = int(request.form["autorizado_por"])
            servicios.componentes_rrhh.autorizarVendedor(vendedor_id, autorizado_por)
            flash("RF1: Vendedor autorizado exitosamente.", "success")
            # notify connected clients (general change)
            for q in list(app.broadcaster):
                try:
                    q.put(json.dumps({"type": "data-changed", "tab": active_tab}))
                except Exception:
                    pass
            # specifically notify that vendedor list changed so clients can refresh selects
            for q in list(app.broadcaster):
                try:
                    q.put(json.dumps({"type": "vendedores-changed"}))
                except Exception:
                    pass
        except PoliMarketError as e:
            flash(f"RF1 Error: {e}", "danger")
        except (ValueError, TypeError) as e:
            flash(f"RF1 Error de entrada: {e}", "danger")
        return redirect(url_for("index", tab=active_tab))

    @app.post("/rf2/crear-pedido")
    def crear_pedido():
        active_tab = request.form.get("active_tab", "tab-rf2")
        try:
            servicios = get_servicios()
            cliente_id = int(request.form["cliente_id"])
            vendedor_id = int(request.form["vendedor_id"])
            items = _parse_items_form()
            pedido_id, estado = servicios.componentes_ventas.crearPedido(cliente_id, vendedor_id, items)
            if estado == "confirmado":
                flash(f"RF2: Pedido #{pedido_id} confirmado. Stock actualizado.", "success")
            else:
                flash(
                    f"RF2: Pedido #{pedido_id} pendiente por falta de stock.",
                    "warning",
                )
            # notify clients
            for q in list(app.broadcaster):
                try:
                    q.put(json.dumps({"type": "data-changed", "tab": active_tab}))
                except Exception:
                    pass
        except PoliMarketError as e:
            flash(f"RF2 Error: {e}", "danger")
        except (ValueError, TypeError) as e:
            flash(f"RF2 Error de entrada: {e}", "danger")
        return redirect(url_for("index", tab=active_tab))

    @app.post("/rf3/verificar-stock")
    def verificar_stock():
        active_tab = request.form.get("active_tab", "tab-rf3")
        try:
            servicios = get_servicios()
            producto_id = int(request.form["producto_id"])
            cantidad = int(request.form["cantidad"])
            disponible = servicios.componentes_stock.verificarDisponibilidad(producto_id, cantidad)
            actual = servicios.componentes_stock.getStockActual(producto_id)
            estado = "SI" if disponible else "NO"
            flash(
                f"RF3: Disponibilidad={estado}, stock actual={actual} unidades.",
                "info",
            )
            for q in list(app.broadcaster):
                try:
                    q.put(json.dumps({"type": "data-changed", "tab": active_tab}))
                except Exception:
                    pass
        except PoliMarketError as e:
            flash(f"RF3 Error: {e}", "danger")
        except (ValueError, TypeError) as e:
            flash(f"RF3 Error de entrada: {e}", "danger")
        return redirect(url_for("index", tab=active_tab))

    @app.post("/rf4/recibir-orden")
    def recibir_orden():
        active_tab = request.form.get("active_tab", "tab-rf4")
        try:
            servicios = get_servicios()
            orden_id = int(request.form["orden_id"])
            items = list(
                servicios.db.conn.execute(
                    "SELECT producto_id, cantidad FROM purchase_order_items WHERE orden_id = ?",
                    (orden_id,),
                )
            )
            if len(items) == 0:
                flash(f"RF4 Error: La orden #{orden_id} no existe o no tiene items.", "danger")
                return redirect(url_for("index", tab=active_tab))
            for item in items:
                servicios.componentes_movimientos.registrarEntrada(
                    int(item["producto_id"]),
                    int(item["cantidad"]),
                    f"Recepcion orden de compra #{orden_id}",
                )
            servicios.componentes_ordenes.confirmarRecepcion(orden_id)
            flash(f"RF4: Orden #{orden_id} recibida y stock repuesto.", "success")
            for q in list(app.broadcaster):
                try:
                    q.put(json.dumps({"type": "data-changed", "tab": active_tab}))
                except Exception:
                    pass
        except PoliMarketError as e:
            flash(f"RF4 Error: {e}", "danger")
        except (ValueError, TypeError) as e:
            flash(f"RF4 Error de entrada: {e}", "danger")
        return redirect(url_for("index", tab=active_tab))

    @app.post("/rf5/programar-entrega")
    def programar_entrega():
        active_tab = request.form.get("active_tab", "tab-rf5")
        try:
            servicios = get_servicios()
            pedido_id = int(request.form["pedido_id"])
            repartidor_id = int(request.form["repartidor_id"])
            fecha_programada = request.form["fecha_programada"]
            entrega_id = servicios.componentes_entregas.programarEntrega(
                pedido_id,
                repartidor_id,
                fecha_programada,
            )
            flash(f"RF5: Entrega #{entrega_id} programada exitosamente.", "success")
            for q in list(app.broadcaster):
                try:
                    q.put(json.dumps({"type": "data-changed", "tab": active_tab}))
                except Exception:
                    pass
        except PoliMarketError as e:
            flash(f"RF5 Error: {e}", "danger")
        except (ValueError, TypeError) as e:
            flash(f"RF5 Error de entrada: {e}", "danger")
        return redirect(url_for("index", tab=active_tab))

    @app.post("/rf5/confirmar-entrega")
    def confirmar_entrega():
        active_tab = request.form.get("active_tab", "tab-rf5")
        try:
            servicios = get_servicios()
            entrega_id = int(request.form["entrega_id"])
            servicios.componentes_entregas.confirmarEntrega(entrega_id)
            estado = servicios.componentes_entregas.getEstadoEntrega(entrega_id)
            flash(f"RF5: Entrega #{entrega_id} confirmada. Estado={estado}.", "success")
            for q in list(app.broadcaster):
                try:
                    q.put(json.dumps({"type": "data-changed", "tab": active_tab}))
                except Exception:
                    pass
        except PoliMarketError as e:
            flash(f"RF5 Error: {e}", "danger")
        except (ValueError, TypeError) as e:
            flash(f"RF5 Error de entrada: {e}", "danger")
        return redirect(url_for("index", tab=active_tab))

    @app.get('/_partial/consultas')
    def partial_consultas():
        servicios = get_servicios()
        vendedores = servicios.componentes_rrhh.listarVendedoresActivos()
        clientes = servicios.componentes_clientes.listarClientes()
        productos = servicios.componentes_catalogo.listarProductos()
        ordenes_pendientes = servicios.componentes_ordenes.listarOrdenesPendientes()
        entregas_pendientes = servicios.componentes_entregas.listarEntregasPendientes()
        stock_actual = {
            row['product_id']: row['cantidad_disponible']
            for row in servicios.db.conn.execute('SELECT product_id, cantidad_disponible FROM stock')
        }
        pedidos = list(servicios.db.conn.execute(
            """
            SELECT o.id, o.fecha, o.estado, o.total, c.nombre AS cliente, e.nombre AS vendedor
            FROM orders o
            JOIN clients c ON c.id = o.cliente_id
            JOIN employees e ON e.id = o.vendedor_id
            ORDER BY o.id DESC
            LIMIT 30
            """
        ))
        return render_template('_consultas.html',
                               vendedores=vendedores,
                               clientes=clientes,
                               productos=productos,
                               ordenes_pendientes=ordenes_pendientes,
                               entregas_pendientes=entregas_pendientes,
                               stock_actual=stock_actual,
                               pedidos=pedidos)

    @app.get('/_partial/rf1_vendedores')
    def partial_rf1_vendedores():
        servicios = get_servicios()
        vendedores = servicios.componentes_rrhh.listarVendedoresActivos()
        return render_template('_rf1_vendedores.html', vendedores=vendedores)

    @app.get('/events')
    def events():
        def gen(q: 'queue.Queue'):
            try:
                while True:
                    data = q.get()
                    yield f"data: {data}\n\n"
            finally:
                try:
                    app.broadcaster.remove(q)
                except Exception:
                    pass

        q = queue.Queue()
        app.broadcaster.append(q)
        return app.response_class(gen(q), mimetype='text/event-stream')

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

