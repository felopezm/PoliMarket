# PoliMarket

## 1. Contexto

PoliMarket opera con cinco areas de negocio: Recursos Humanos, Ventas, Bodega, Proveedores y Entregas.  
El flujo principal es:

1. RRHH autoriza vendedores.
2. Ventas crea y confirma pedidos para clientes.
3. Ventas y Entregas consultan Bodega para disponibilidad.
4. Bodega dispara reposicion a Proveedores cuando el stock baja del minimo.
5. Entregas programa y confirma la distribucion, registrando salidas de inventario.

---

## 2. Diagrama de clases UML (vista logica) y Diagrama de componentes

![Diagrama](./docs/Diagrama%20de%20clases%20UML%20GoF.png)
![Diagrama](./docs/PoliMarket%20-%20Diagrama%20de%20Componentes%20con%20Patrones%20GoF.png)
---

## 3. Tabla de componentes

| Area de negocio | Componente | Funcionalidades expuestas |
| --- | --- | --- |
| Recursos Humanos | ComponenteRRHH | `autorizarVendedor`, `revocarAutorizacion`, `verificarAutorizacion`, `listarVendedoresActivos` |
| Recursos Humanos | ComponenteEmpleados | `registrarEmpleado`, `actualizarEmpleado`, `getEmpleado`, `listarEmpleados` |
| Ventas | ComponenteVentas | `crearPedido`, `confirmarPedido`, `cancelarPedido`, `listarPedidosPorVendedor` |
| Ventas | ComponenteClientes | `registrarCliente`, `getCliente`, `listarClientes`, `getHistorialCompras` |
| Ventas | ComponenteCatalogo | `getProducto`, `listarProductos`, `buscarProducto`, `getPrecio` |
| Bodega | ComponenteStock | `verificarDisponibilidad`, `reducirStock`, `reponerStock`, `getStockActual` |
| Bodega | ComponenteMovimientos | `registrarSalida`, `registrarEntrada`, `getHistorialMovimientos` |
| Proveedores | ComponenteOrdenesCompra | `emitirOrdenCompra`, `emitirOrdenCompraPorProducto`, `confirmarRecepcion`, `listarOrdenesPendientes`, `getOrden` |
| Entregas | ComponenteEntregas | `programarEntrega`, `confirmarEntrega`, `getEstadoEntrega`, `listarEntregasPendientes` |
| Entregas | ComponenteLogistica | `asignarRepartidor`, `registrarSalidaBodega`, `getPedidosPorEntregar` |

---

## 4. Relaciones entre componentes

| Origen | Consume | Objetivo |
| --- | --- | --- |
| ComponenteVentas | IAutorizacion (equivalente) | ComponenteRRHH |
| ComponenteVentas | IStock (equivalente) | ComponenteStock |
| ComponenteStock | IOrdenesCompra (equivalente) | ComponenteOrdenesCompra |
| ComponenteEntregas | IMovimientos (equivalente) | ComponenteMovimientos |
| ComponenteEntregas | IPedidos (equivalente) | ComponenteVentas |

---

## 5. Cobertura de requerimientos funcionales

| Requisito | Implementacion en `app.py` |
| --- | --- |
| RF1 - Autorizar vendedor | `ComponenteRRHH.autorizarVendedor` y `verificarAutorizacion` bloqueando pedidos no autorizados |
| RF2 - Crear y confirmar pedido | `ComponenteVentas.crearPedido` + `confirmarPedido`, con calculo de total y cambio de estado |
| RF3 - Verificar disponibilidad de stock | `ComponenteStock.verificarDisponibilidad` usado por Ventas y Entregas |
| RF4 - Emitir orden de compra a proveedor | `ComponenteStock` dispara `ComponenteOrdenesCompra.emitirOrdenCompraPorProducto` bajo umbral minimo |
| RF5 - Programar y confirmar entrega | `ComponenteEntregas.programarEntrega` + `confirmarEntrega`, incluyendo salidas de bodega y cierre del pedido |

---
## 6 Clientes
 - Cliente 1  (Consola - Python)
 - Cliente 2 (Aplicación Web - Flask - Python)

## 6.1. Estructura final por carpetas (Clientes y compartida)

La solucion quedo separada por interfaz y con logica compartida:

- `app/src_shared/`  
  Clases, metodos y conexion a base de datos compartidos por consola y web.
  - `database.py`
  - `components.py`
  - `models.py`
  - `common.py`
  - `bootstrap.py`

- `app/src_consola/`  
  Interfaz de consola.
  - `app.py`
  - `console.py`

- `app/src_web/`  
  Interfaz web con Flask.
  - `app.py`
  - `templates/index.html`

La base de datos SQLite compartida por ambas aplicaciones:

`app/polimarket.db`

---

## 7 Ejecucion independiente de cada cliente

Instalar dependencias:

`py -3 -m pip install -r app/requirements.txt`

Ejecutar cliente de consola:

`py -3 app/src_consola/app.py`

Ejecutar cliente web Flask:

`py -3 app/src_web/app.py`

Luego abrir en navegador:

`http://127.0.0.1:5000`

---

## 8. Cobertura funcional en cliente web

La aplicacion Flask implementa los mismos RF:

- RF1: autorizar vendedor.
- RF2: crear y confirmar pedido.
- RF3: verificar disponibilidad de stock.
- RF4: confirmar recepcion de ordenes de compra (las ordenes se generan automaticamente cuando stock cae bajo minimo).
- RF5: programar y confirmar entrega.

---

## 9. Patrones de diseno GoF

[#9-patrones-de-diseno-gof](#9-patrones-de-diseno-gof)

A partir del diagrama de clases UML v2 (Facade, Proxy, Chain of Responsibility,
Strategy, Observer, Builder y State), se incorporo la carpeta
`app/src_shared/patterns/` con la implementacion de seis de esos patrones.
Facade no se duplica como codigo nuevo porque ya esta cubierto
estructuralmente por las clases `Componente*` de `components.py`, que son
el unico punto de entrada de cada modulo de negocio.

| Patron | Archivo | Donde se conecta con la app real |
| --- | --- | --- |
| State | `patterns/estados.py` | `ComponenteVentas.cancelarPedido` valida la transicion antes de escribir en `orders` (antes se podia cancelar un pedido ya entregado) |
| Strategy | `patterns/precio_strategy.py` | `ComponenteVentas.crearPedido` elige la estrategia de precio segun el historial del cliente o un codigo de promocion |
| Chain of Responsibility | `patterns/validadores_autorizacion.py` | Encadena zona asignada -> credito -> autorizacion RRHH |
| Proxy | `patterns/ventas_proxy.py` | `bootstrap.crear_servicios` inyecta `ProxyVentas` (no `ComponenteVentas`) como `componentes_ventas`; corre la cadena de autorizacion antes de delegar |
| Builder | `patterns/orden_compra_builder.py` | `ComponenteOrdenesCompra.emitirOrdenCompra` arma la orden con el builder, evitando ordenes sin items |
| Observer | `patterns/stock_observer.py` | `ComponenteStock` es ahora un `StockSubject`; notifica a `NotificadorOrdenesCompra` en vez de llamar directamente a `ComponenteOrdenesCompra` |

De paso se corrigieron dos defectos reales encontrados durante la
implementacion: un metodo `crearPedido` duplicado dentro de
`ComponenteVentas` (la segunda definicion pisaba silenciosamente a la
primera) y la posibilidad de registrar una orden de compra sin items.

Pruebas: `app/tests/test_patrones_gof.py` (19 casos, incluye pruebas de
cada patron de forma aislada y pruebas de integracion contra la base de
datos real).

```bash
py -3 -m pip install -r app/requirements-dev.txt
cd app && py -3 -m pytest tests/test_patrones_gof.py -v
```

---

