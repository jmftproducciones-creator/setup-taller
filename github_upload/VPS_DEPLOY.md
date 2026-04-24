# Despliegue en VPS

La guía principal actualizada está en [DESPLIEGUE_VPS_ACTUALIZADO.md](DESPLIEGUE_VPS_ACTUALIZADO.md).

La guía de imports productivos está en [SETUP_IMPORT_VPS.md](SETUP_IMPORT_VPS.md).

Guia base original para referencia:

## 1. Paquetes del servidor

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mysql-server nginx
```

## 2. Carpeta del proyecto

Ejemplo usando `/var/www/sput`:

```bash
sudo mkdir -p /var/www/sput
sudo chown -R $USER:www-data /var/www/sput
```

Subi los archivos del proyecto a esa carpeta. No subas `.env` real a repositorios publicos.

## 3. Entorno Python

```bash
cd /var/www/sput
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Configuracion

```bash
cp .env.example .env
nano .env
```

Valores importantes:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=setup_user
DB_PASSWORD=clave_segura
DB_NAME=setup_db
AUTO_INIT_DB=0
FLASK_DEBUG=0
ABRIR_WORD_AL_CREAR=0
ABRIR_WORD_AL_MODIFICAR=0
```

`AUTO_INIT_DB=0` es lo recomendado para produccion. La base se inicializa con `init_db.py` o desde `systemd` antes de arrancar.

## 5. MySQL

Entrar a MySQL como root:

```bash
sudo mysql
```

Crear base y usuario:

```sql
CREATE DATABASE IF NOT EXISTS setup_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'setup_user'@'localhost' IDENTIFIED BY 'clave_segura';
GRANT ALL PRIVILEGES ON setup_db.* TO 'setup_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Inicializar tablas:

```bash
cd /var/www/sput
source .venv/bin/activate
python init_db.py
```

## 6. Probar la app

```bash
gunicorn -c deploy/gunicorn.conf.py wsgi:application
```

En otra terminal:

```bash
curl http://127.0.0.1:5000/
```

## 7. Servicio systemd

Editar `deploy/sput.service` si tu ruta no es `/var/www/sput`.

```bash
sudo cp deploy/sput.service /etc/systemd/system/sput.service
sudo chown -R www-data:www-data /var/www/sput
sudo systemctl daemon-reload
sudo systemctl enable --now sput
sudo systemctl status sput
```

Ver logs:

```bash
sudo journalctl -u sput -f
```

## 8. Nginx

Editar `deploy/nginx-sput.conf` y cambiar:

```nginx
server_name ejemplo.com www.ejemplo.com;
```

Instalar configuracion:

```bash
sudo cp deploy/nginx-sput.conf /etc/nginx/sites-available/sput
sudo ln -s /etc/nginx/sites-available/sput /etc/nginx/sites-enabled/sput
sudo nginx -t
sudo systemctl reload nginx
```

## 9. SSL

Con dominio apuntando al VPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ejemplo.com -d www.ejemplo.com
```

## 10. Backups

El script `deploy/backup_mysql.sh` respalda MySQL y `docx_ordenes`.

```bash
chmod +x deploy/backup_mysql.sh
sudo APP_DIR=/var/www/sput BACKUP_DIR=/var/backups/sput deploy/backup_mysql.sh
```

Cron diario ejemplo:

```bash
sudo crontab -e
```

Agregar:

```cron
30 2 * * * APP_DIR=/var/www/sput BACKUP_DIR=/var/backups/sput /var/www/sput/deploy/backup_mysql.sh
```

## Notas

- En VPS no se abre Word automaticamente. Los DOCX se generan en `docx_ordenes`.
- El usuario que corre el servicio debe poder escribir en `docx_ordenes`.
- No uses `root/root` en produccion.
- Para cada cliente serio conviene usar una base separada o un VPS separado.
