from dataclasses import dataclass
from pathlib import Path

from .components import (
    # implementations 
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
    # interface 
    IComponenteCatalogo,
    IComponenteClientes,
    IComponenteEmpleados,
    IComponenteEntregas,
    IComponenteLogistica,
    IComponenteMovimientos,
    IComponenteOrdenesCompra,
    IComponenteRRHH,
    IComponenteStock,
    IComponenteVentas,
)
from .database import Database


@dataclass
class PoliMarketServicios:
    db: Database
    componentes_empleados: IComponenteEmpleados
    componentes_rrhh: IComponenteRRHH
    componentes_catalogo: IComponenteCatalogo
    componentes_clientes: IComponenteClientes
    componentes_ordenes: IComponenteOrdenesCompra
    componentes_stock: IComponenteStock
    componentes_movimientos: IComponenteMovimientos
    componentes_ventas: IComponenteVentas
    componentes_entregas: IComponenteEntregas
    componentes_logistica: IComponenteLogistica


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
        componentes_movimientos,
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

