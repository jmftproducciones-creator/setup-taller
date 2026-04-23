import os
from pathlib import Path

import mysql.connector
from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parent


def load_env_file(path: Path = BASE_DIR / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

BRANCHES = {
    "central": {
        "name": os.getenv("BRANCH_CENTRAL_NAME", "Sucursal Verde"),
        "database": os.getenv("DB_NAME_CENTRAL", os.getenv("DB_NAME", "setup")),
        "theme": "central",
    },
    "naranja": {
        "name": os.getenv("BRANCH_NARANJA_NAME", "Sucursal Naranja"),
        "database": os.getenv("DB_NAME_NARANJA", "setup_naranja"),
        "theme": "naranja",
    },
}

DEFAULT_ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_NAME = os.getenv("DEFAULT_ADMIN_NAME", "Administrador")

DEFAULT_USERS = [
    {
        "username": DEFAULT_ADMIN_USER,
        "display_name": DEFAULT_ADMIN_NAME,
        "password": DEFAULT_ADMIN_PASSWORD,
        "email": "admin@setup.local",
        "telefono": "",
        "is_admin": 1,
        "branches": ["central", "naranja"],
    },
    {
        "username": "federico",
        "display_name": "Federico",
        "password": "federico123",
        "email": "federico@setup.local",
        "telefono": "",
        "is_admin": 0,
        "branches": ["central", "naranja"],
    },
    {
        "username": "willi",
        "display_name": "Willi",
        "password": "willi123",
        "email": "willi@setup.local",
        "telefono": "",
        "is_admin": 0,
        "branches": ["central", "naranja"],
    },
    {
        "username": "felipe",
        "display_name": "Felipe",
        "password": "felipe123",
        "email": "felipe@setup.local",
        "telefono": "",
        "is_admin": 0,
        "branches": ["central"],
    },
    {
        "username": "naranja1",
        "display_name": "Operador Naranja 1",
        "password": "naranja123",
        "email": "naranja1@setup.local",
        "telefono": "",
        "is_admin": 0,
        "branches": ["naranja"],
    },
    {
        "username": "naranja2",
        "display_name": "Operador Naranja 2",
        "password": "naranja123",
        "email": "naranja2@setup.local",
        "telefono": "",
        "is_admin": 0,
        "branches": ["naranja"],
    },
]


SHARED_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS clientes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(255) NOT NULL,
        direccion VARCHAR(255) NULL,
        localidad VARCHAR(120) NULL,
        provincia VARCHAR(120) NULL,
        cp VARCHAR(30) NULL,
        telefono VARCHAR(60) NULL,
        celular VARCHAR(60) NULL,
        email VARCHAR(255) NULL,
        cuit VARCHAR(40) NULL,
        contacto VARCHAR(255) NULL,
        observaciones TEXT NULL,
        giro_empresa VARCHAR(255) NULL,
        cliente_garantia TINYINT(1) NOT NULL DEFAULT 0,
        cliente_con_contrato TINYINT(1) NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_clientes_nombre (nombre),
        KEY idx_clientes_telefono (telefono)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS equipos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        descripcion VARCHAR(255) NULL,
        serie VARCHAR(160) NULL,
        serie_norm VARCHAR(160) NULL,
        tipo VARCHAR(120) NULL,
        marca VARCHAR(120) NULL,
        modelo VARCHAR(120) NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_equipos_serie_norm (serie_norm),
        KEY idx_equipos_descripcion (descripcion)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS equipo_cliente (
        id INT AUTO_INCREMENT PRIMARY KEY,
        equipo_id INT NOT NULL,
        cliente_id INT NOT NULL,
        rol VARCHAR(80) NOT NULL DEFAULT 'propietario',
        fecha_asignacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        UNIQUE KEY uq_equipo_cliente (equipo_id, cliente_id),
        KEY idx_equipo_cliente_activo (equipo_id, activo),
        CONSTRAINT fk_equipo_cliente_equipo
            FOREIGN KEY (equipo_id) REFERENCES equipos(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_equipo_cliente_cliente
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

BRANCH_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS fallas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        descripcion VARCHAR(255) NOT NULL,
        UNIQUE KEY uq_fallas_descripcion (descripcion)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS reparaciones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        descripcion VARCHAR(255) NOT NULL,
        UNIQUE KEY uq_reparaciones_descripcion (descripcion)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS repuestos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(255) NOT NULL,
        descripcion TEXT NULL,
        costo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
        UNIQUE KEY uq_repuestos_nombre (nombre),
        KEY idx_repuestos_nombre (nombre)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS accesorios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(255) NOT NULL,
        UNIQUE KEY uq_accesorios_nombre (nombre)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ordenes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        fecha DATE NOT NULL,
        hora_ingreso TIME NULL,
        cliente_id INT NOT NULL,
        equipo_id INT NOT NULL,
        falla TEXT NULL,
        observaciones TEXT NULL,
        accesorios TEXT NULL,
        reparacion TEXT NULL,
        repuestos TEXT NULL,
        importe DECIMAL(12,2) NOT NULL DEFAULT 0.00,
        estado VARCHAR(80) NOT NULL DEFAULT 'EN REPARACION',
        fecha_salida DATE NULL,
        hora_salida TIME NULL,
        fecha_regreso DATE NULL,
        hora_regreso TIME NULL,
        fecha_retiro DATE NULL,
        hora_retiro TIME NULL,
        fecha_terminada DATE NULL,
        hora_terminada TIME NULL,
        presupuesto_aprobado TINYINT(1) NOT NULL DEFAULT 0,
        sucursal_key VARCHAR(50) NULL,
        registrado_por VARCHAR(120) NULL,
        registrado_por_nombre VARCHAR(120) NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_ordenes_estado (estado),
        KEY idx_ordenes_fecha (fecha),
        KEY idx_ordenes_cliente (cliente_id),
        KEY idx_ordenes_equipo (equipo_id),
        KEY idx_ordenes_sucursal (sucursal_key),
        KEY idx_ordenes_registrado_por (registrado_por)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS orden_historial (
        id INT AUTO_INCREMENT PRIMARY KEY,
        orden_id INT NOT NULL,
        usuario VARCHAR(120) NOT NULL DEFAULT 'sistema',
        accion VARCHAR(80) NOT NULL,
        nota TEXT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_historial_orden (orden_id),
        CONSTRAINT fk_historial_orden
            FOREIGN KEY (orden_id) REFERENCES ordenes(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

AUTH_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS sucursales (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sucursal_key VARCHAR(50) NOT NULL,
        nombre VARCHAR(120) NOT NULL,
        tema VARCHAR(50) NOT NULL,
        activa TINYINT(1) NOT NULL DEFAULT 1,
        UNIQUE KEY uq_sucursales_key (sucursal_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(120) NOT NULL,
        display_name VARCHAR(120) NOT NULL,
        email VARCHAR(255) NULL,
        telefono VARCHAR(80) NULL,
        password_hash VARCHAR(255) NOT NULL,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        is_admin TINYINT(1) NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_usuarios_username (username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS usuario_sucursal (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        sucursal_key VARCHAR(50) NOT NULL,
        UNIQUE KEY uq_usuario_sucursal (usuario_id, sucursal_key),
        CONSTRAINT fk_usuario_sucursal_usuario
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

SEED_DATA = [
    ("fallas", "descripcion", ["No enciende", "No imprime", "Falla intermitente"]),
    ("reparaciones", "descripcion", ["Revision", "Limpieza", "Cambio de repuesto"]),
]


def server_connection(database: str | None = None):
    params = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
    }
    if database:
        params["database"] = database
    return mysql.connector.connect(**params)


def ensure_database(database_name: str) -> None:
    conn = server_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.close()
    conn.close()


def setup_branch_database(database_name: str) -> None:
    ensure_database(database_name)
    conn = server_connection(database_name)
    cur = conn.cursor()
    for statement in BRANCH_TABLES:
        cur.execute(statement)
    cur.close()

    ensure_column(conn, "ordenes", "sucursal_key", "VARCHAR(50) NULL AFTER presupuesto_aprobado")
    ensure_column(conn, "ordenes", "registrado_por", "VARCHAR(120) NULL AFTER sucursal_key")
    ensure_column(conn, "ordenes", "registrado_por_nombre", "VARCHAR(120) NULL AFTER registrado_por")
    drop_foreign_key_if_exists(conn, "ordenes", "fk_ordenes_cliente")
    drop_foreign_key_if_exists(conn, "ordenes", "fk_ordenes_equipo")

    cur = conn.cursor()

    for table, column, values in SEED_DATA:
        for value in values:
            cur.execute(
                f"INSERT IGNORE INTO `{table}` (`{column}`) VALUES (%s)",
                (value,),
            )

    conn.commit()
    cur.close()
    conn.close()


def ensure_column(conn, table_name: str, column_name: str, definition: str) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    exists = cur.fetchone()
    if not exists:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
    cur.close()


def drop_foreign_key_if_exists(conn, table_name: str, constraint_name: str) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND CONSTRAINT_NAME = %s
          AND CONSTRAINT_TYPE = 'FOREIGN KEY'
        LIMIT 1
        """,
        (table_name, constraint_name),
    )
    exists = cur.fetchone()
    if exists:
        cur.execute(f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name}")
    cur.close()


def setup_shared_tables() -> None:
    database_name = BRANCHES["central"]["database"]
    ensure_database(database_name)
    conn = server_connection(database_name)
    cur = conn.cursor()
    for statement in SHARED_TABLES:
        cur.execute(statement)
    conn.commit()
    cur.close()
    conn.close()


def setup_auth_database() -> None:
    auth_database = BRANCHES["central"]["database"]
    ensure_database(auth_database)
    conn = server_connection(auth_database)
    cur = conn.cursor()

    for statement in AUTH_TABLES:
        cur.execute(statement)
    cur.close()

    ensure_column(conn, "usuarios", "email", "VARCHAR(255) NULL AFTER display_name")
    ensure_column(conn, "usuarios", "telefono", "VARCHAR(80) NULL AFTER email")
    ensure_column(conn, "usuarios", "is_admin", "TINYINT(1) NOT NULL DEFAULT 0 AFTER activo")

    cur = conn.cursor()

    for branch_key, branch in BRANCHES.items():
        cur.execute(
            """
            INSERT INTO sucursales (sucursal_key, nombre, tema, activa)
            VALUES (%s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                nombre=VALUES(nombre),
                tema=VALUES(tema),
                activa=1
            """,
            (branch_key, branch["name"], branch["theme"]),
        )

    for user in DEFAULT_USERS:
        cur.execute(
            """
            INSERT INTO usuarios (username, display_name, email, telefono, password_hash, activo, is_admin)
            VALUES (%s, %s, %s, %s, %s, 1, %s)
            ON DUPLICATE KEY UPDATE
                display_name=VALUES(display_name),
                email=VALUES(email),
                telefono=VALUES(telefono),
                activo=1,
                is_admin=VALUES(is_admin)
            """,
            (
                user["username"],
                user["display_name"],
                user["email"],
                user["telefono"],
                generate_password_hash(user["password"]),
                user["is_admin"],
            ),
        )
        cur.execute("SELECT id FROM usuarios WHERE username=%s LIMIT 1", (user["username"],))
        user_id = cur.fetchone()[0]
        for branch_key in user["branches"]:
            cur.execute(
                """
                INSERT IGNORE INTO usuario_sucursal (usuario_id, sucursal_key)
                VALUES (%s, %s)
                """,
                (user_id, branch_key),
            )

    conn.commit()
    cur.close()
    conn.close()


def main() -> None:
    setup_shared_tables()
    for branch in BRANCHES.values():
        setup_branch_database(branch["database"])
    setup_auth_database()
    print(f"Bases listas: auth-en={BRANCHES['central']['database']}, sucursales={', '.join(branch['database'] for branch in BRANCHES.values())}")
    print("Usuarios iniciales: " + ", ".join(user["username"] for user in DEFAULT_USERS))


if __name__ == "__main__":
    main()
