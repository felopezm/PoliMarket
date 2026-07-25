from pathlib import Path
import sqlite3


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def initialize(self) -> None:
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL,
                cargo TEXT NOT NULL,
                estado TEXT NOT NULL,
                is_seller INTEGER NOT NULL DEFAULT 0,
                codigo_vendedor TEXT,
                zona TEXT
            );

            CREATE TABLE IF NOT EXISTS seller_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL UNIQUE,
                fecha_autorizacion TEXT NOT NULL,
                authorized_by INTEGER NOT NULL,
                activa INTEGER NOT NULL,
                FOREIGN KEY (seller_id) REFERENCES employees(id),
                FOREIGN KEY (authorized_by) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                telefono TEXT NOT NULL,
                email TEXT NOT NULL,
                direccion TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                nit TEXT NOT NULL,
                contacto TEXT NOT NULL,
                email TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                precio REAL NOT NULL,
                categoria TEXT NOT NULL,
                default_provider_id INTEGER NOT NULL,
                FOREIGN KEY (default_provider_id) REFERENCES providers(id)
            );

            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL UNIQUE,
                cantidad_disponible INTEGER NOT NULL,
                cantidad_minima INTEGER NOT NULL,
                ubicacion TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                referencia TEXT NOT NULL,
                FOREIGN KEY (stock_id) REFERENCES stock(id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                vendedor_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                estado TEXT NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clients(id),
                FOREIGN KEY (vendedor_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS order_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL NOT NULL,
                FOREIGN KEY (pedido_id) REFERENCES orders(id),
                FOREIGN KEY (producto_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                estado TEXT NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (proveedor_id) REFERENCES providers(id)
            );

            CREATE TABLE IF NOT EXISTS purchase_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_acordado REAL NOT NULL,
                FOREIGN KEY (orden_id) REFERENCES purchase_orders(id),
                FOREIGN KEY (producto_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL UNIQUE,
                repartidor_id INTEGER NOT NULL,
                fecha_programada TEXT NOT NULL,
                fecha_real TEXT,
                estado TEXT NOT NULL,
                direccion_destino TEXT NOT NULL,
                FOREIGN KEY (pedido_id) REFERENCES orders(id),
                FOREIGN KEY (repartidor_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS delivery_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entrega_id INTEGER NOT NULL,
                movimiento_id INTEGER NOT NULL,
                FOREIGN KEY (entrega_id) REFERENCES deliveries(id),
                FOREIGN KEY (movimiento_id) REFERENCES stock_movements(id)
            );
            """
        )
        self.conn.commit()

    def seed(self) -> None:
        existing = self.conn.execute("SELECT COUNT(1) FROM employees").fetchone()[0]
        if existing > 0:
            return

        self.conn.executescript(
            """
            INSERT INTO employees (nombre, email, cargo, estado, is_seller, codigo_vendedor, zona)
            VALUES
                ('Ana RRHH', 'ana.rrhh@polimarket.com', 'RRHH', 'activo', 0, NULL, NULL),
                ('Carlos Vendedor', 'carlos.vendedor@polimarket.com', 'Vendedor', 'activo', 1, 'V001', 'Norte'),
                ('Laura Repartidora', 'laura.reparto@polimarket.com', 'Repartidor', 'activo', 0, NULL, NULL);

            INSERT INTO clients (nombre, telefono, email, direccion)
            VALUES ('Juan Perez', '3001234567', 'juan.perez@email.com', 'Calle 10 #20-30');

            INSERT INTO providers (nombre, nit, contacto, email)
            VALUES ('Tech Supplier SAS', '900111222-3', 'Maria Compras', 'compras@techsupplier.com');

            INSERT INTO products (nombre, descripcion, precio, categoria, default_provider_id)
            VALUES
                ('Laptop Pro 14', 'Portatil de alto rendimiento', 4200.0, 'Tecnologia', 1),
                ('Mouse Inalambrico', 'Mouse ergonomico', 80.0, 'Tecnologia', 1);

            INSERT INTO stock (product_id, cantidad_disponible, cantidad_minima, ubicacion)
            VALUES
                (1, 10, 4, 'A1-B2'),
                (2, 2, 3, 'A1-C5');
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
