# SPUT

Versión lista para publicar en un repositorio nuevo.

Incluye:

- app Flask principal
- login por usuarios
- sucursal verde y sucursal naranja
- clientes y equipos compartidos
- órdenes separadas por sucursal
- panel admin de usuarios
- scripts `setup_import` para clientes y repuestos
- archivos de deploy para VPS

## Estructura principal

- `app.py`
- `init_db.py`
- `wsgi.py`
- `requirements.txt`
- `templates/`
- `static/`
- `deploy/`
- `setup_import/`

## Documentación

- `DESPLIEGUE_VPS_ACTUALIZADO.md`
- `SETUP_IMPORT_VPS.md`
- `VPS_DEPLOY.md`

## Notas

- No subir `.env` real al repositorio.
- Antes de desplegar en VPS, revisar el `.env.example`.
- Para producción, correr `python init_db.py` luego de instalar dependencias.
