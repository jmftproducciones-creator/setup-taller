# Despliegue VPS Actualizado

Esta guía deja el sistema actual listo en el VPS con:

- login por usuarios
- sucursal verde y sucursal naranja
- clientes y equipos compartidos
- órdenes separadas por sucursal
- panel admin de usuarios
- scripts `setup_import` para actualizar clientes y repuestos

## 1. Subir archivos

Subí al VPS todo este proyecto, incluyendo:

- `app.py`
- `init_db.py`
- `wsgi.py`
- `requirements.txt`
- `templates/`
- `static/`
- `deploy/`
- `setup_import/`
- `orden_docx.py`
- `docx_ordenes/` si querés conservar DOCX generados

## 2. Variables `.env`

Usá un `.env` parecido a este:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=setup_user
DB_PASSWORD=clave_segura

DB_NAME=setup
DB_NAME_CENTRAL=setup
DB_NAME_NARANJA=setup_naranja

SECRET_KEY=cambiar-por-una-clave-larga
AUTO_INIT_DB=0
FLASK_DEBUG=0
APP_HOST=0.0.0.0
PORT=5000

BRANCH_CENTRAL_NAME=Sucursal Verde
BRANCH_NARANJA_NAME=Sucursal Naranja

DEFAULT_ADMIN_USER=admin
DEFAULT_ADMIN_PASSWORD=admin123
DEFAULT_ADMIN_NAME=Administrador

ABRIR_WORD_AL_CREAR=0
ABRIR_WORD_AL_MODIFICAR=0
```

## 3. Base de datos MySQL

Entrá como root:

```bash
sudo mysql
```

Creá bases y usuario:

```sql
CREATE DATABASE IF NOT EXISTS setup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS setup_naranja CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'setup_user'@'localhost' IDENTIFIED BY 'clave_segura';
GRANT ALL PRIVILEGES ON setup.* TO 'setup_user'@'localhost';
GRANT ALL PRIVILEGES ON setup_naranja.* TO 'setup_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 4. Entorno virtual

```bash
cd /var/www/sput
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Inicializar esquema

Esto crea o actualiza:

- tablas compartidas en `setup`
- tablas de órdenes por sucursal
- tablas de usuarios/permisos
- usuarios iniciales

```bash
cd /var/www/sput
source .venv/bin/activate
python init_db.py
```

## 6. Cómo queda la lógica de datos

- `setup`: clientes, equipos, usuarios, permisos y sucursal verde
- `setup_naranja`: órdenes de sucursal naranja y sus catálogos operativos

Importante:

- un cliente cargado en una sucursal aparece en ambas
- un equipo cargado en una sucursal aparece en ambas
- una orden solo aparece en la sucursal donde fue creada
- la lista de órdenes muestra quién la registró y en qué sucursal

## 7. Servicio

El servicio actual ya ejecuta `init_db.py` antes de arrancar:

```ini
ExecStartPre=/var/www/sput/.venv/bin/python /var/www/sput/init_db.py
```

Reinstalación/reinicio:

```bash
sudo cp deploy/sput.service /etc/systemd/system/sput.service
sudo systemctl daemon-reload
sudo systemctl enable --now sput
sudo systemctl restart sput
sudo systemctl status sput
```

## 8. Verificación rápida

Logueate con:

- usuario: `admin`
- contraseña: `admin123`

Luego verificá:

- pestaña `Usuarios`
- cambio entre sucursal verde y naranja
- cliente compartido entre sucursales
- orden visible solo en su sucursal

## 9. Logs

```bash
sudo journalctl -u sput -f
```

