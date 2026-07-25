from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class Empleado:
    id: int
    nombre: str
    email: str
    cargo: str
    estado: str

    def getInfo(self) -> str:
        return f"{self.id} - {self.nombre} ({self.cargo})"

    def estaActivo(self) -> bool:
        return self.estado.lower() == "activo"


@dataclass
class Vendedor(Empleado):
    codigoVendedor: str
    zona: str

    def getSolicitudesAsignadas(self) -> List[str]:
        return []

    def getClientesAsignados(self) -> List[str]:
        return []


@dataclass
class AutorizacionVendedor:
    id: int
    vendedor_id: int
    fechaAutorizacion: str
    autorizadoPor: int
    activa: bool

    def autorizar(self) -> None:
        self.activa = True

    def revocar(self) -> None:
        self.activa = False

    def isVigente(self) -> bool:
        return self.activa


@dataclass
class Cliente:
    id: int
    nombre: str
    telefono: str
    email: str
    direccion: str

    def getHistorialCompras(self) -> List[str]:
        return []

    def getDatos(self) -> str:
        return f"{self.id} - {self.nombre} ({self.telefono})"


@dataclass
class Producto:
    id: int
    nombre: str
    descripcion: str
    precio: float
    categoria: str

    def getPrecio(self) -> float:
        return self.precio

    def getInfo(self) -> str:
        return f"{self.id} - {self.nombre} - ${self.precio:.2f}"


@dataclass
class Pedido:
    id: int
    cliente_id: int
    vendedor_id: int
    fecha: str
    estado: str
    total: float

    def calcularTotal(self, subtotales: Sequence[float]) -> float:
        self.total = sum(subtotales)
        return self.total

    def confirmar(self) -> None:
        self.estado = "confirmado"

    def cancelar(self) -> None:
        self.estado = "cancelado"


@dataclass
class DetallePedido:
    id: int
    pedido_id: int
    producto_id: int
    cantidad: int
    precioUnitario: float

    def getSubtotal(self) -> float:
        return self.cantidad * self.precioUnitario


@dataclass
class Stock:
    id: int
    producto_id: int
    cantidadDisponible: int
    cantidadMinima: int
    ubicacion: str

    def estaDisponible(self, cantidad: int) -> bool:
        return self.cantidadDisponible >= cantidad

    def reducirStock(self, cantidad: int) -> None:
        if cantidad > self.cantidadDisponible:
            raise ValueError("No hay stock suficiente.")
        self.cantidadDisponible -= cantidad

    def reponerStock(self, cantidad: int) -> None:
        self.cantidadDisponible += cantidad


@dataclass
class MovimientoStock:
    id: int
    stock_id: int
    tipo: str
    cantidad: int
    fecha: str
    referencia: str

    def registrar(self) -> None:
        return None

    def getDetalle(self) -> str:
        return f"{self.fecha} - {self.tipo} - {self.cantidad} ({self.referencia})"


@dataclass
class Proveedor:
    id: int
    nombre: str
    nit: str
    contacto: str
    email: str

    def getProductosOfrecidos(self) -> List[str]:
        return []

    def getDatos(self) -> str:
        return f"{self.id} - {self.nombre}"


@dataclass
class OrdenCompra:
    id: int
    proveedor_id: int
    fecha: str
    estado: str
    total: float

    def emitir(self) -> None:
        self.estado = "pendiente"

    def confirmarRecepcion(self) -> None:
        self.estado = "recibida"

    def getItems(self) -> List[str]:
        return []


@dataclass
class ItemOrdenCompra:
    id: int
    orden_id: int
    producto_id: int
    cantidad: int
    precioAcordado: float

    def getSubtotal(self) -> float:
        return self.cantidad * self.precioAcordado


@dataclass
class Entrega:
    id: int
    pedido_id: int
    repartidor_id: int
    fechaProgramada: str
    fechaReal: str | None
    estado: str
    direccionDestino: str

    def programar(self) -> None:
        self.estado = "programada"

    def confirmarEntrega(self) -> None:
        self.estado = "entregada"

    def getEstado(self) -> str:
        return self.estado


@dataclass
class DetalleEntrega:
    id: int
    entrega_id: int
    movimiento_id: int

    def registrarSalida(self) -> None:
        return None

