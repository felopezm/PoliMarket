from __future__ import annotations

import sqlite3
from typing import List, Sequence, Optional

from .common import now_iso
from .database import Database
from .exceptions import EntidadNoEncontrada, ReglaDeNegocio, VendedorNoAutorizado

from abc import ABC, abstractmethod


# Interfaces (ABCs) 
class IComponenteEmpleados(ABC):
    @abstractmethod
    def registrarEmpleado(self, datos: dict) -> int: ...

    @abstractmethod
    def actualizarEmpleado(self, employee_id: int, datos: dict) -> None: ...

    @abstractmethod
    def getEmpleado(self, employee_id: int) -> Optional[sqlite3.Row]: ...

    @abstractmethod
    def listarEmpleados(self) -> List[sqlite3.Row]: ...


class IComponenteRRHH(ABC):
    @abstractmethod
    def autorizarVendedor(self, vendedor_id: int, autorizado_por: int) -> None: ...

    @abstractmethod
    def revocarAutorizacion(self, vendedor_id: int) -> None: ...

    @abstractmethod
    def verificarAutorizacion(self, vendedor_id: int) -> bool: ...

    @abstractmethod
    def listarVendedoresActivos(self) -> List[sqlite3.Row]: ...


class IComponenteCatalogo(ABC):
    @abstractmethod
    def getProducto(self, producto_id: int) -> Optional[sqlite3.Row]: ...

    @abstractmethod
    def listarProductos(self) -> List[sqlite3.Row]: ...

    @abstractmethod
    def buscarProducto(self, filtro: str) -> List[sqlite3.Row]: ...

    @abstractmethod
    def getPrecio(self, producto_id: int) -> float: ...


class IComponenteClientes(ABC):
    @abstractmethod
    def registrarCliente(self, datos: dict) -> int: ...

    @abstractmethod
    def getCliente(self, cliente_id: int) -> Optional[sqlite3.Row]: ...

    @abstractmethod
    def listarClientes(self) -> List[sqlite3.Row]: ...

    @abstractmethod
    def getHistorialCompras(self, cliente_id: int) -> List[sqlite3.Row]: ...


class IComponenteOrdenesCompra(ABC):
    @abstractmethod
    def emitirOrdenCompra(self, proveedor_id: int, items: Sequence[tuple[int, int, float]]) -> int: ...

    @abstractmethod
    def emitirOrdenCompraPorProducto(self, producto_id: int, cantidad_sugerida: int) -> Optional[int]: ...

    @abstractmethod
    def confirmarRecepcion(self, orden_id: int) -> None: ...

    @abstractmethod
    def listarOrdenesPendientes(self) -> List[sqlite3.Row]: ...

    @abstractmethod
    def getOrden(self, orden_id: int) -> Optional[sqlite3.Row]: ...


class IComponenteStock(ABC):
    @abstractmethod
    def verificarDisponibilidad(self, producto_id: int, cantidad: int) -> bool: ...

    @abstractmethod
    def reducirStock(self, producto_id: int, cantidad: int) -> None: ...

    @abstractmethod
    def reponerStock(self, producto_id: int, cantidad: int) -> None: ...

    @abstractmethod
    def getStockActual(self, producto_id: int) -> int: ...


class IComponenteMovimientos(ABC):
    @abstractmethod
    def registrarSalida(self, producto_id: int, cantidad: int, referencia: str) -> int: ...

    @abstractmethod
    def registrarEntrada(self, producto_id: int, cantidad: int, referencia: str) -> int: ...

    @abstractmethod
    def getHistorialMovimientos(self, producto_id: int) -> List[sqlite3.Row]: ...


class IComponenteVentas(ABC):
    @abstractmethod
    def crearPedido(self, cliente_id: int, vendedor_id: int, items: Sequence[tuple[int, int]]) -> tuple[int, str]: ...

    @abstractmethod
    def confirmarPedido(self, pedido_id: int) -> bool: ...

    @abstractmethod
    def cancelarPedido(self, pedido_id: int) -> None: ...

    @abstractmethod
    def listarPedidosPorVendedor(self, vendedor_id: int) -> List[sqlite3.Row]: ...


class IComponenteEntregas(ABC):
    @abstractmethod
    def programarEntrega(self, pedido_id: int, repartidor_id: int, fecha: str) -> int: ...

    @abstractmethod
    def confirmarEntrega(self, entrega_id: int) -> None: ...

    @abstractmethod
    def getEstadoEntrega(self, entrega_id: int) -> str: ...

    @abstractmethod
    def listarEntregasPendientes(self) -> List[sqlite3.Row]: ...


class IComponenteLogistica(ABC):
    @abstractmethod
    def asignarRepartidor(self, entrega_id: int, repartidor_id: int) -> None: ...

    @abstractmethod
    def registrarSalidaBodega(self, entrega_id: int) -> None: ...

    @abstractmethod
    def getPedidosPorEntregar(self) -> List[sqlite3.Row]: ...



class ComponenteEmpleados(IComponenteEmpleados):
    def __init__(self, db: Database) -> None:
        self.db = db

    def registrarEmpleado(self, datos: dict) -> int:
        cursor = self.db.conn.execute(
            """
            INSERT INTO employees (nombre, email, cargo, estado, is_seller, codigo_vendedor, zona)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datos["nombre"],
                datos["email"],
                datos["cargo"],
                datos["estado"],
                int(datos.get("is_seller", False)),
                datos.get("codigo_vendedor"),
                datos.get("zona"),
            ),
        )
        self.db.conn.commit()
        return int(cursor.lastrowid)

    def actualizarEmpleado(self, employee_id: int, datos: dict) -> None:
        if self.getEmpleado(employee_id) is None:
            raise EntidadNoEncontrada(f"Empleado con ID={employee_id} no encontrado.")
        self.db.conn.execute(
            """
            UPDATE employees
            SET nombre = ?, email = ?, cargo = ?, estado = ?, codigo_vendedor = ?, zona = ?
            WHERE id = ?
            """,
            (
                datos["nombre"],
                datos["email"],
                datos["cargo"],
                datos["estado"],
                datos.get("codigo_vendedor"),
                datos.get("zona"),
                employee_id,
            ),
        )
        self.db.conn.commit()

    def getEmpleado(self, employee_id: int) -> sqlite3.Row | None:
        return self.db.conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()

    def listarEmpleados(self) -> List[sqlite3.Row]:
        return list(self.db.conn.execute("SELECT * FROM employees ORDER BY id"))


class ComponenteRRHH(IComponenteRRHH):
    def __init__(self, db: Database) -> None:
        self.db = db

    def autorizarVendedor(self, vendedor_id: int, autorizado_por: int) -> None:
        seller = self.db.conn.execute(
            "SELECT id FROM employees WHERE id = ? AND is_seller = 1 AND estado = 'activo'",
            (vendedor_id,),
        ).fetchone()
        if seller is None:
            raise EntidadNoEncontrada(
                f"Vendedor con ID={vendedor_id} no encontrado o no esta activo."
            )

        autorizador = self.db.conn.execute(
            "SELECT id FROM employees WHERE id = ? AND estado = 'activo'",
            (autorizado_por,),
        ).fetchone()
        if autorizador is None:
            raise EntidadNoEncontrada(
                f"Empleado autorizador con ID={autorizado_por} no encontrado o no esta activo."
            )

        existing = self.db.conn.execute(
            "SELECT id FROM seller_authorizations WHERE seller_id = ?",
            (vendedor_id,),
        ).fetchone()
        if existing:
            self.db.conn.execute(
                """
                UPDATE seller_authorizations
                SET activa = 1, fecha_autorizacion = ?, authorized_by = ?
                WHERE seller_id = ?
                """,
                (now_iso(), autorizado_por, vendedor_id),
            )
        else:
            self.db.conn.execute(
                """
                INSERT INTO seller_authorizations (seller_id, fecha_autorizacion, authorized_by, activa)
                VALUES (?, ?, ?, 1)
                """,
                (vendedor_id, now_iso(), autorizado_por),
            )
        self.db.conn.commit()

    def revocarAutorizacion(self, vendedor_id: int) -> None:
        auth = self.db.conn.execute(
            "SELECT id FROM seller_authorizations WHERE seller_id = ?",
            (vendedor_id,),
        ).fetchone()
        if auth is None:
            raise EntidadNoEncontrada(
                f"No existe autorizacion registrada para el vendedor con ID={vendedor_id}."
            )
        self.db.conn.execute(
            "UPDATE seller_authorizations SET activa = 0 WHERE seller_id = ?",
            (vendedor_id,),
        )
        self.db.conn.commit()

    def verificarAutorizacion(self, vendedor_id: int) -> bool:
        row = self.db.conn.execute(
            """
            SELECT sa.activa
            FROM seller_authorizations sa
            JOIN employees e ON e.id = sa.seller_id
            WHERE sa.seller_id = ? AND e.estado = 'activo'
            """,
            (vendedor_id,),
        ).fetchone()
        return bool(row and row["activa"] == 1)

    def listarVendedoresActivos(self) -> List[sqlite3.Row]:
        return list(
            self.db.conn.execute(
                """
                SELECT e.id, e.nombre, e.codigo_vendedor, e.zona,
                       COALESCE(sa.activa, 0) AS autorizado
                FROM employees e
                LEFT JOIN seller_authorizations sa ON sa.seller_id = e.id
                WHERE e.is_seller = 1 AND e.estado = 'activo'
                ORDER BY e.id
                """
            )
        )


class ComponenteCatalogo(IComponenteCatalogo):
    def __init__(self, db: Database) -> None:
        self.db = db

    def getProducto(self, producto_id: int) -> sqlite3.Row | None:
        return self.db.conn.execute("SELECT * FROM products WHERE id = ?", (producto_id,)).fetchone()

    def listarProductos(self) -> List[sqlite3.Row]:
        return list(self.db.conn.execute("SELECT * FROM products ORDER BY id"))

    def buscarProducto(self, filtro: str) -> List[sqlite3.Row]:
        like_filter = f"%{filtro}%"
        return list(
            self.db.conn.execute(
                """
                SELECT * FROM products
                WHERE nombre LIKE ? OR descripcion LIKE ? OR categoria LIKE ?
                ORDER BY id
                """,
                (like_filter, like_filter, like_filter),
            )
        )

    def getPrecio(self, producto_id: int) -> float:
        product = self.getProducto(producto_id)
        if product is None:
            raise EntidadNoEncontrada(f"Producto con ID={producto_id} no encontrado.")
        return float(product["precio"])


class ComponenteClientes(IComponenteClientes):
    def __init__(self, db: Database) -> None:
        self.db = db

    def registrarCliente(self, datos: dict) -> int:
        cursor = self.db.conn.execute(
            """
            INSERT INTO clients (nombre, telefono, email, direccion)
            VALUES (?, ?, ?, ?)
            """,
            (datos["nombre"], datos["telefono"], datos["email"], datos["direccion"]),
        )
        self.db.conn.commit()
        return int(cursor.lastrowid)

    def getCliente(self, cliente_id: int) -> sqlite3.Row | None:
        return self.db.conn.execute("SELECT * FROM clients WHERE id = ?", (cliente_id,)).fetchone()

    def listarClientes(self) -> List[sqlite3.Row]:
        return list(self.db.conn.execute("SELECT * FROM clients ORDER BY id"))

    def getHistorialCompras(self, cliente_id: int) -> List[sqlite3.Row]:
        if self.getCliente(cliente_id) is None:
            raise EntidadNoEncontrada(f"Cliente con ID={cliente_id} no encontrado.")
        return list(
            self.db.conn.execute(
                """
                SELECT id, fecha, estado, total
                FROM orders
                WHERE cliente_id = ?
                ORDER BY id DESC
                """,
                (cliente_id,),
            )
        )


class ComponenteOrdenesCompra(IComponenteOrdenesCompra):
    def __init__(self, db: Database) -> None:
        self.db = db

    def emitirOrdenCompra(self, proveedor_id: int, items: Sequence[tuple[int, int, float]]) -> int:
        proveedor = self.db.conn.execute(
            "SELECT id FROM providers WHERE id = ?", (proveedor_id,)
        ).fetchone()
        if proveedor is None:
            raise EntidadNoEncontrada(f"Proveedor con ID={proveedor_id} no encontrado.")
        total = sum(cantidad * precio for _, cantidad, precio in items)
        cursor = self.db.conn.execute(
            """
            INSERT INTO purchase_orders (proveedor_id, fecha, estado, total)
            VALUES (?, ?, 'pendiente', ?)
            """,
            (proveedor_id, now_iso(), total),
        )
        order_id = int(cursor.lastrowid)
        for producto_id, cantidad, precio in items:
            self.db.conn.execute(
                """
                INSERT INTO purchase_order_items (orden_id, producto_id, cantidad, precio_acordado)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, producto_id, cantidad, precio),
            )
        self.db.conn.commit()
        return order_id

    def emitirOrdenCompraPorProducto(self, producto_id: int, cantidad_sugerida: int) -> int | None:
        pending = self.db.conn.execute(
            """
            SELECT poi.id
            FROM purchase_order_items poi
            JOIN purchase_orders po ON po.id = poi.orden_id
            WHERE poi.producto_id = ? AND po.estado = 'pendiente'
            """,
            (producto_id,),
        ).fetchone()
        if pending:
            return None

        product = self.db.conn.execute(
            "SELECT default_provider_id, precio FROM products WHERE id = ?",
            (producto_id,),
        ).fetchone()
        if product is None:
            raise EntidadNoEncontrada(
                f"Producto con ID={producto_id} no encontrado para generar orden de compra."
            )

        return self.emitirOrdenCompra(
            int(product["default_provider_id"]),
            [(producto_id, cantidad_sugerida, float(product["precio"]))],
        )

    def confirmarRecepcion(self, orden_id: int) -> None:
        orden = self.db.conn.execute(
            "SELECT id, estado FROM purchase_orders WHERE id = ?", (orden_id,)
        ).fetchone()
        if orden is None:
            raise EntidadNoEncontrada(f"Orden de compra con ID={orden_id} no encontrada.")
        if orden["estado"] != "pendiente":
            raise ReglaDeNegocio(
                f"La orden #{orden_id} no esta en estado pendiente (estado actual: {orden['estado']})."
            )
        self.db.conn.execute(
            "UPDATE purchase_orders SET estado = 'recibida' WHERE id = ?",
            (orden_id,),
        )
        self.db.conn.commit()

    def listarOrdenesPendientes(self) -> List[sqlite3.Row]:
        return list(
            self.db.conn.execute(
                """
                SELECT po.id, p.nombre AS proveedor, po.fecha, po.total
                FROM purchase_orders po
                JOIN providers p ON p.id = po.proveedor_id
                WHERE po.estado = 'pendiente'
                ORDER BY po.id
                """
            )
        )

    def getOrden(self, orden_id: int) -> sqlite3.Row | None:
        return self.db.conn.execute("SELECT * FROM purchase_orders WHERE id = ?", (orden_id,)).fetchone()


class ComponenteStock(IComponenteStock):
    def __init__(self, db: Database, componente_ordenes: ComponenteOrdenesCompra) -> None:
        self.db = db
        self.componente_ordenes = componente_ordenes

    def verificarDisponibilidad(self, producto_id: int, cantidad: int) -> bool:
        stock = self.db.conn.execute(
            "SELECT * FROM stock WHERE product_id = ?",
            (producto_id,),
        ).fetchone()
        if stock is None:
            raise EntidadNoEncontrada(
                f"No existe registro de stock para el producto con ID={producto_id}."
            )

        if stock["cantidad_disponible"] < stock["cantidad_minima"]:
            sugerida = max((stock["cantidad_minima"] * 2) - stock["cantidad_disponible"], stock["cantidad_minima"])
            self.componente_ordenes.emitirOrdenCompraPorProducto(producto_id, int(sugerida))

        return stock["cantidad_disponible"] >= cantidad

    def reducirStock(self, producto_id: int, cantidad: int) -> None:
        stock = self.db.conn.execute(
            "SELECT * FROM stock WHERE product_id = ?",
            (producto_id,),
        ).fetchone()
        if stock is None:
            raise EntidadNoEncontrada(
                f"No existe registro de stock para el producto con ID={producto_id}."
            )
        if stock["cantidad_disponible"] < cantidad:
            raise ReglaDeNegocio(
                f"Stock insuficiente para el producto ID={producto_id}. "
                f"Disponible: {stock['cantidad_disponible']}, solicitado: {cantidad}."
            )

        nuevo_stock = int(stock["cantidad_disponible"]) - cantidad
        self.db.conn.execute(
            "UPDATE stock SET cantidad_disponible = ? WHERE product_id = ?",
            (nuevo_stock, producto_id),
        )
        self.db.conn.commit()
        self.verificarDisponibilidad(producto_id, 0)

    def reponerStock(self, producto_id: int, cantidad: int) -> None:
        stock = self.db.conn.execute(
            "SELECT id FROM stock WHERE product_id = ?", (producto_id,)
        ).fetchone()
        if stock is None:
            raise EntidadNoEncontrada(
                f"No existe registro de stock para el producto con ID={producto_id}."
            )
        self.db.conn.execute(
            "UPDATE stock SET cantidad_disponible = cantidad_disponible + ? WHERE product_id = ?",
            (cantidad, producto_id),
        )
        self.db.conn.commit()

    def getStockActual(self, producto_id: int) -> int:
        row = self.db.conn.execute(
            "SELECT cantidad_disponible FROM stock WHERE product_id = ?",
            (producto_id,),
        ).fetchone()
        if row is None:
            raise EntidadNoEncontrada(
                f"No existe registro de stock para el producto con ID={producto_id}."
            )
        return int(row["cantidad_disponible"])


class ComponenteMovimientos(IComponenteMovimientos):
    def __init__(self, db: Database, componente_stock: ComponenteStock) -> None:
        self.db = db
        self.componente_stock = componente_stock

    def registrarSalida(self, producto_id: int, cantidad: int, referencia: str) -> int:
        self.componente_stock.reducirStock(producto_id, cantidad)
        stock = self.db.conn.execute("SELECT id FROM stock WHERE product_id = ?", (producto_id,)).fetchone()
        cursor = self.db.conn.execute(
            """
            INSERT INTO stock_movements (stock_id, tipo, cantidad, fecha, referencia)
            VALUES (?, 'salida', ?, ?, ?)
            """,
            (int(stock["id"]), cantidad, now_iso(), referencia),
        )
        self.db.conn.commit()
        return int(cursor.lastrowid)

    def registrarEntrada(self, producto_id: int, cantidad: int, referencia: str) -> int:
        self.componente_stock.reponerStock(producto_id, cantidad)
        stock = self.db.conn.execute("SELECT id FROM stock WHERE product_id = ?", (producto_id,)).fetchone()
        cursor = self.db.conn.execute(
            """
            INSERT INTO stock_movements (stock_id, tipo, cantidad, fecha, referencia)
            VALUES (?, 'entrada', ?, ?, ?)
            """,
            (int(stock["id"]), cantidad, now_iso(), referencia),
        )
        self.db.conn.commit()
        return int(cursor.lastrowid)

    def getHistorialMovimientos(self, producto_id: int) -> List[sqlite3.Row]:
        return list(
            self.db.conn.execute(
                """
                SELECT sm.id, sm.tipo, sm.cantidad, sm.fecha, sm.referencia
                FROM stock_movements sm
                JOIN stock s ON s.id = sm.stock_id
                WHERE s.product_id = ?
                ORDER BY sm.id DESC
                """,
                (producto_id,),
            )
        )


class ComponenteVentas(IComponenteVentas):
    def __init__(
        self,
        db: Database,
        componente_rrhh: ComponenteRRHH,
        componente_stock: ComponenteStock,
        componente_catalogo: ComponenteCatalogo,
        componente_movimientos: "ComponenteMovimientos",
    ) -> None:
        self.db = db
        self.componente_rrhh = componente_rrhh
        self.componente_stock = componente_stock
        self.componente_catalogo = componente_catalogo
        self.componente_movimientos = componente_movimientos

    def crearPedido(self, cliente_id: int, vendedor_id: int, items: Sequence[tuple[int, int]]) -> tuple[int, str]:
        # Validar que el cliente exista
        cliente = self.db.conn.execute(
            "SELECT id FROM clients WHERE id = ?", (cliente_id,)
        ).fetchone()
        if cliente is None:
            raise EntidadNoEncontrada(f"Cliente con ID={cliente_id} no encontrado.")

        # Validar que el vendedor exista y este activo
        vendedor = self.db.conn.execute(
            "SELECT id FROM employees WHERE id = ? AND is_seller = 1 AND estado = 'activo'",
            (vendedor_id,),
        ).fetchone()
        if vendedor is None:
            raise EntidadNoEncontrada(
                f"Vendedor con ID={vendedor_id} no encontrado o no esta activo."
            )

        # Validar autorizacion RRHH
        if not self.componente_rrhh.verificarAutorizacion(vendedor_id):
            raise VendedorNoAutorizado(
                f"El vendedor con ID={vendedor_id} no tiene autorizacion activa de RRHH."
            )

        disponibilidad_completa = True
        detalles: List[tuple[int, int, float]] = []
        for producto_id, cantidad in items:
            precio = self.componente_catalogo.getPrecio(producto_id)
            detalles.append((producto_id, cantidad, precio))
            if not self.componente_stock.verificarDisponibilidad(producto_id, cantidad):
                disponibilidad_completa = False

        estado_inicial = "creado" if disponibilidad_completa else "pendiente_sin_stock"
        cursor = self.db.conn.execute(
            """
            INSERT INTO orders (cliente_id, vendedor_id, fecha, estado, total)
            VALUES (?, ?, ?, ?, 0)
            """,
            (cliente_id, vendedor_id, now_iso(), estado_inicial),
        )
        pedido_id = int(cursor.lastrowid)

        for producto_id, cantidad, precio in detalles:
            self.db.conn.execute(
                """
                INSERT INTO order_details (pedido_id, producto_id, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
                """,
                (pedido_id, producto_id, cantidad, precio),
            )
        self.db.conn.commit()

        if disponibilidad_completa:
            self.confirmarPedido(pedido_id)
            return pedido_id, "confirmado"
        return pedido_id, "pendiente_sin_stock"

    def confirmarPedido(self, pedido_id: int) -> bool:
        pedido = self.db.conn.execute("SELECT id FROM orders WHERE id = ?", (pedido_id,)).fetchone()
        if pedido is None:
            raise EntidadNoEncontrada(f"Pedido con ID={pedido_id} no encontrado.")

        detalles = list(
            self.db.conn.execute(
                "SELECT producto_id, cantidad, precio_unitario FROM order_details WHERE pedido_id = ?",
                (pedido_id,),
            )
        )
        if len(detalles) == 0:
            raise ReglaDeNegocio(f"El pedido #{pedido_id} no tiene productos asociados.")

        for detalle in detalles:
            if not self.componente_stock.verificarDisponibilidad(int(detalle["producto_id"]), int(detalle["cantidad"])):
                self.db.conn.execute(
                    "UPDATE orders SET estado = 'pendiente_sin_stock' WHERE id = ?",
                    (pedido_id,),
                )
                self.db.conn.commit()
                return False

        # Reducir stock y registrar salida al confirmar el pedido
        for detalle in detalles:
            self.componente_movimientos.registrarSalida(
                int(detalle["producto_id"]),
                int(detalle["cantidad"]),
                f"Pedido #{pedido_id} confirmado",
            )

        total = sum(float(d["precio_unitario"]) * int(d["cantidad"]) for d in detalles)
        self.db.conn.execute(
            "UPDATE orders SET estado = 'confirmado', total = ? WHERE id = ?",
            (total, pedido_id),
        )
        self.db.conn.commit()
        return True

    def cancelarPedido(self, pedido_id: int) -> None:
        pedido = self.db.conn.execute("SELECT id FROM orders WHERE id = ?", (pedido_id,)).fetchone()
        if pedido is None:
            raise EntidadNoEncontrada(f"Pedido con ID={pedido_id} no encontrado.")
        self.db.conn.execute("UPDATE orders SET estado = 'cancelado' WHERE id = ?", (pedido_id,))
        self.db.conn.commit()

    def listarPedidosPorVendedor(self, vendedor_id: int) -> List[sqlite3.Row]:
        vendedor = self.db.conn.execute(
            "SELECT id FROM employees WHERE id = ? AND is_seller = 1", (vendedor_id,)
        ).fetchone()
        if vendedor is None:
            raise EntidadNoEncontrada(f"Vendedor con ID={vendedor_id} no encontrado.")
        return list(
            self.db.conn.execute(
                """
                SELECT id, fecha, estado, total
                FROM orders
                WHERE vendedor_id = ?
                ORDER BY id DESC
                """,
                (vendedor_id,),
            )
        )


    def crearPedido(self, cliente_id: int, vendedor_id: int, items: Sequence[tuple[int, int]]) -> tuple[int, str]:
        # Validar que el cliente exista
        cliente = self.db.conn.execute(
            "SELECT id FROM clients WHERE id = ?", (cliente_id,)
        ).fetchone()
        if cliente is None:
            raise EntidadNoEncontrada(f"Cliente con ID={cliente_id} no encontrado.")

        # Validar que el vendedor exista y este activo
        vendedor = self.db.conn.execute(
            "SELECT id FROM employees WHERE id = ? AND is_seller = 1 AND estado = 'activo'",
            (vendedor_id,),
        ).fetchone()
        if vendedor is None:
            raise EntidadNoEncontrada(
                f"Vendedor con ID={vendedor_id} no encontrado o no esta activo."
            )

        # Validar autorizacion RRHH
        if not self.componente_rrhh.verificarAutorizacion(vendedor_id):
            raise VendedorNoAutorizado(
                f"El vendedor con ID={vendedor_id} no tiene autorizacion activa de RRHH."
            )

        disponibilidad_completa = True
        detalles: List[tuple[int, int, float]] = []
        for producto_id, cantidad in items:
            precio = self.componente_catalogo.getPrecio(producto_id)
            detalles.append((producto_id, cantidad, precio))
            if not self.componente_stock.verificarDisponibilidad(producto_id, cantidad):
                disponibilidad_completa = False

        estado_inicial = "creado" if disponibilidad_completa else "pendiente_sin_stock"
        cursor = self.db.conn.execute(
            """
            INSERT INTO orders (cliente_id, vendedor_id, fecha, estado, total)
            VALUES (?, ?, ?, ?, 0)
            """,
            (cliente_id, vendedor_id, now_iso(), estado_inicial),
        )
        pedido_id = int(cursor.lastrowid)

        for producto_id, cantidad, precio in detalles:
            self.db.conn.execute(
                """
                INSERT INTO order_details (pedido_id, producto_id, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
                """,
                (pedido_id, producto_id, cantidad, precio),
            )
        self.db.conn.commit()

        if disponibilidad_completa:
            self.confirmarPedido(pedido_id)
            return pedido_id, "confirmado"
        return pedido_id, "pendiente_sin_stock"



class ComponenteEntregas(IComponenteEntregas):
    def __init__(self, db: Database, componente_movimientos: ComponenteMovimientos) -> None:
        self.db = db
        self.componente_movimientos = componente_movimientos

    def programarEntrega(self, pedido_id: int, repartidor_id: int, fecha: str) -> int:
        pedido = self.db.conn.execute(
            """
            SELECT o.id, o.estado, c.direccion
            FROM orders o
            JOIN clients c ON c.id = o.cliente_id
            WHERE o.id = ?
            """,
            (pedido_id,),
        ).fetchone()
        if pedido is None:
            raise EntidadNoEncontrada(f"Pedido con ID={pedido_id} no encontrado.")
        if pedido["estado"] != "confirmado":
            raise ReglaDeNegocio(
                f"El pedido #{pedido_id} no esta confirmado (estado actual: {pedido['estado']}). "
                "Solo se pueden programar pedidos confirmados."
            )

        repartidor = self.db.conn.execute(
            "SELECT id FROM employees WHERE id = ? AND estado = 'activo'", (repartidor_id,)
        ).fetchone()
        if repartidor is None:
            raise EntidadNoEncontrada(
                f"Repartidor con ID={repartidor_id} no encontrado o no esta activo."
            )

        with self.db.conn:
            cursor = self.db.conn.execute(
                """
                INSERT INTO deliveries (pedido_id, repartidor_id, fecha_programada, fecha_real, estado, direccion_destino)
                VALUES (?, ?, ?, NULL, 'programada', ?)
                """,
                (pedido_id, repartidor_id, fecha, pedido["direccion"]),
            )
            entrega_id = int(cursor.lastrowid)

            self.db.conn.execute(
                "UPDATE orders SET estado = 'en_entrega' WHERE id = ?",
                (pedido_id,),
            )
        return entrega_id

    def confirmarEntrega(self, entrega_id: int) -> None:
        entrega = self.db.conn.execute(
            "SELECT pedido_id, estado FROM deliveries WHERE id = ?",
            (entrega_id,),
        ).fetchone()
        if entrega is None:
            raise EntidadNoEncontrada(f"Entrega con ID={entrega_id} no encontrada.")
        if entrega["estado"] == "entregada":
            raise ReglaDeNegocio(f"La entrega #{entrega_id} ya fue confirmada anteriormente.")
        with self.db.conn:
            self.db.conn.execute(
                "UPDATE deliveries SET estado = 'entregada', fecha_real = ? WHERE id = ?",
                (now_iso(), entrega_id),
            )
            self.db.conn.execute(
                "UPDATE orders SET estado = 'entregado' WHERE id = ?",
                (int(entrega["pedido_id"]),),
            )

    def getEstadoEntrega(self, entrega_id: int) -> str:
        entrega = self.db.conn.execute("SELECT estado FROM deliveries WHERE id = ?", (entrega_id,)).fetchone()
        if entrega is None:
            raise EntidadNoEncontrada(f"Entrega con ID={entrega_id} no encontrada.")
        return str(entrega["estado"])

    def listarEntregasPendientes(self) -> List[sqlite3.Row]:
        return list(
            self.db.conn.execute(
                """
                SELECT id, pedido_id, repartidor_id, fecha_programada, estado
                FROM deliveries
                WHERE estado = 'programada'
                ORDER BY id
                """
            )
        )


class ComponenteLogistica(IComponenteLogistica):
    def __init__(self, db: Database, componente_entregas: ComponenteEntregas) -> None:
        self.db = db
        self.componente_entregas = componente_entregas

    def asignarRepartidor(self, entrega_id: int, repartidor_id: int) -> None:
        if self.db.conn.execute("SELECT id FROM deliveries WHERE id = ?", (entrega_id,)).fetchone() is None:
            raise EntidadNoEncontrada(f"Entrega con ID={entrega_id} no encontrada.")
        if self.db.conn.execute(
            "SELECT id FROM employees WHERE id = ? AND estado = 'activo'", (repartidor_id,)
        ).fetchone() is None:
            raise EntidadNoEncontrada(
                f"Repartidor con ID={repartidor_id} no encontrado o no esta activo."
            )
        self.db.conn.execute(
            "UPDATE deliveries SET repartidor_id = ? WHERE id = ?",
            (repartidor_id, entrega_id),
        )
        self.db.conn.commit()

    def registrarSalidaBodega(self, entrega_id: int) -> None:
        estado = self.componente_entregas.getEstadoEntrega(entrega_id)
        if estado != "programada":
            raise ReglaDeNegocio(
                f"La entrega #{entrega_id} no esta programada (estado actual: {estado})."
            )

    def getPedidosPorEntregar(self) -> List[sqlite3.Row]:
        return list(
            self.db.conn.execute(
                "SELECT id, cliente_id, vendedor_id, total FROM orders WHERE estado = 'confirmado' ORDER BY id"
            )
        )

