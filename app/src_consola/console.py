from pathlib import Path
from typing import List

from src_shared import PoliMarketServicios, crear_servicios


class ConsolaPoliMarket:
    def __init__(self, servicios: PoliMarketServicios) -> None:
        self.servicios = servicios

    @classmethod
    def desde_db_compartida(cls) -> "ConsolaPoliMarket":
        db_path = Path(__file__).resolve().parents[1] / "polimarket.db"
        return cls(crear_servicios(db_path))

    def ejecutar(self) -> None:
        while True:
            print("\n=== PoliMarket Cliente 1 (Consola) ===")
            print("1. Listar vendedores activos y autorizacion (RF1)")
            print("2. Autorizar vendedor (RF1)")
            print("3. Crear y confirmar pedido (RF2)")
            print("4. Verificar disponibilidad de stock (RF3)")
            print("5. Programar entrega (RF5)")
            print("6. Confirmar entrega (RF5)")
            print("7. Listar ordenes de compra pendientes (RF4)")
            print("8. Confirmar recepcion de orden de compra (RF4)")
            print("9. Salir")
            opcion = input("Seleccione una opcion: ").strip()

            if opcion == "1":
                self._listar_vendedores()
            elif opcion == "2":
                self._autorizar_vendedor()
            elif opcion == "3":
                self._crear_pedido()
            elif opcion == "4":
                self._verificar_stock()
            elif opcion == "5":
                self._programar_entrega()
            elif opcion == "6":
                self._confirmar_entrega()
            elif opcion == "7":
                self._listar_ordenes_compra()
            elif opcion == "8":
                self._recibir_orden_compra()
            elif opcion == "9":
                print("Saliendo...")
                break
            else:
                print("Opcion invalida.")

    def _listar_vendedores(self) -> None:
        vendedores = self.servicios.componentes_rrhh.listarVendedoresActivos()
        if not vendedores:
            print("No hay vendedores activos.")
            return
        print("\nVendedores activos:")
        for vendedor in vendedores:
            estado = "SI" if vendedor["autorizado"] == 1 else "NO"
            print(
                f"ID={vendedor['id']} | Nombre={vendedor['nombre']} | "
                f"Codigo={vendedor['codigo_vendedor']} | Zona={vendedor['zona']} | Autorizado={estado}"
            )

    def _autorizar_vendedor(self) -> None:
        vendedor_id = int(input("ID de vendedor a autorizar: ").strip())
        autorizado_por = int(input("ID de empleado RRHH que autoriza: ").strip())
        self.servicios.componentes_rrhh.autorizarVendedor(vendedor_id, autorizado_por)
        print("Vendedor autorizado correctamente.")

    def _crear_pedido(self) -> None:
        vendedor_id = int(input("ID de vendedor: ").strip())
        cliente_id = int(input("ID de cliente: ").strip())
        print("\nProductos disponibles:")
        for producto in self.servicios.componentes_catalogo.listarProductos():
            print(
                f"ID={producto['id']} | {producto['nombre']} | "
                f"Precio=${float(producto['precio']):.2f}"
            )

        items: List[tuple[int, int]] = []
        while True:
            producto_id_txt = input("Producto ID (vacio para terminar): ").strip()
            if producto_id_txt == "":
                break
            cantidad = int(input("Cantidad: ").strip())
            items.append((int(producto_id_txt), cantidad))

        if len(items) == 0:
            raise ValueError("Debe agregar al menos un producto.")

        pedido_id, estado = self.servicios.componentes_ventas.crearPedido(cliente_id, vendedor_id, items)
        print(f"Pedido #{pedido_id} creado.")
        if estado == "confirmado":
            print("Pedido confirmado y disponible para Entregas.")
        else:
            print("Pedido en estado pendiente por falta de stock.")

    def _verificar_stock(self) -> None:
        producto_id = int(input("ID de producto: ").strip())
        cantidad = int(input("Cantidad a verificar: ").strip())
        disponible = self.servicios.componentes_stock.verificarDisponibilidad(producto_id, cantidad)
        actual = self.servicios.componentes_stock.getStockActual(producto_id)
        print(f"Stock actual: {actual}")
        print("Disponibilidad: SI" if disponible else "Disponibilidad: NO")

    def _programar_entrega(self) -> None:
        pedido_id = int(input("ID del pedido confirmado: ").strip())
        repartidor_id = int(input("ID del repartidor: ").strip())
        fecha = input("Fecha programada (YYYY-MM-DD): ").strip()
        entrega_id = self.servicios.componentes_entregas.programarEntrega(pedido_id, repartidor_id, fecha)
        print(f"Entrega #{entrega_id} programada.")

    def _confirmar_entrega(self) -> None:
        entrega_id = int(input("ID de entrega: ").strip())
        self.servicios.componentes_entregas.confirmarEntrega(entrega_id)
        estado = self.servicios.componentes_entregas.getEstadoEntrega(entrega_id)
        print(f"Entrega #{entrega_id} confirmada. Estado actual: {estado}.")

    def _listar_ordenes_compra(self) -> None:
        ordenes = self.servicios.componentes_ordenes.listarOrdenesPendientes()
        if not ordenes:
            print("No hay ordenes pendientes.")
            return
        for orden in ordenes:
            print(
                f"Orden #{orden['id']} | Proveedor: {orden['proveedor']} | "
                f"Fecha: {orden['fecha']} | Total: ${float(orden['total']):.2f}"
            )

    def _recibir_orden_compra(self) -> None:
        orden_id = int(input("ID de orden de compra recibida: ").strip())
        items = list(
            self.servicios.db.conn.execute(
                "SELECT producto_id, cantidad FROM purchase_order_items WHERE orden_id = ?",
                (orden_id,),
            )
        )
        if len(items) == 0:
            raise ValueError("La orden no tiene items.")
        for item in items:
            self.servicios.componentes_movimientos.registrarEntrada(
                int(item["producto_id"]),
                int(item["cantidad"]),
                f"Recepcion orden de compra #{orden_id}",
            )
        self.servicios.componentes_ordenes.confirmarRecepcion(orden_id)
        print(f"Orden #{orden_id} recibida y stock repuesto.")

