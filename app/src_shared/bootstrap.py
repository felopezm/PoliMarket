from dataclasses import dataclass
from pathlib import Path

from .components import (
    ComponenteCatalogo,
    ComponenteClientes,
    ComponenteEmpleados,
    ComponenteEntregas,
    ComponenteLogistica,
    ComponenteMovimientos,
    ComponenteOrdenesCompra,
    ComponenteRRHH,
    ComponenteStock,
    ComponenteVentas,
)
from .database import Database


@dataclass
class PoliMarketServicios:
    db: Database
    componentes_empleados: ComponenteEmpleados
    componentes_rrhh: ComponenteRRHH
    componentes_catalogo: ComponenteCatalogo
    componentes_clientes: ComponenteClientes
    componentes_ordenes: ComponenteOrdenesCompra
    componentes_stock: ComponenteStock
    componentes_movimientos: ComponenteMovimientos
    componentes_ventas: ComponenteVentas
    componentes_entregas: ComponenteEntregas
    componentes_logistica: ComponenteLogistica


def crear_servicios(db_path: Path) -> PoliMarketServicios:
    db = Database(db_path)
    db.initialize()
    db.seed()

    componentes_empleados = ComponenteEmpleados(db)
    componentes_rrhh = ComponenteRRHH(db)
    componentes_catalogo = ComponenteCatalogo(db)
    componentes_clientes = ComponenteClientes(db)
    componentes_ordenes = ComponenteOrdenesCompra(db)
    componentes_stock = ComponenteStock(db, componentes_ordenes)
    componentes_movimientos = ComponenteMovimientos(db, componentes_stock)
    componentes_ventas = ComponenteVentas(
        db,
        componentes_rrhh,
        componentes_stock,
        componentes_catalogo,
    )
    componentes_entregas = ComponenteEntregas(db, componentes_movimientos)
    componentes_logistica = ComponenteLogistica(db, componentes_entregas)

    return PoliMarketServicios(
        db=db,
        componentes_empleados=componentes_empleados,
        componentes_rrhh=componentes_rrhh,
        componentes_catalogo=componentes_catalogo,
        componentes_clientes=componentes_clientes,
        componentes_ordenes=componentes_ordenes,
        componentes_stock=componentes_stock,
        componentes_movimientos=componentes_movimientos,
        componentes_ventas=componentes_ventas,
        componentes_entregas=componentes_entregas,
        componentes_logistica=componentes_logistica,
    )

