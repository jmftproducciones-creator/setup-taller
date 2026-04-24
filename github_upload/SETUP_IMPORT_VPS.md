# Setup Import en VPS

Esta guía explica cómo usar `setup_import` en el VPS para actualizar:

- clientes compartidos
- repuestos

## 1. Dónde viven los datos importados

### Clientes

Los clientes son compartidos entre sucursales.

Por eso el script de clientes usa la base:

- `DB_NAME`
- normalmente `setup`

### Repuestos

Los repuestos hoy se actualizan contra la base configurada en `.env`.

Entonces:

- si `DB_NAME=setup`, importás repuestos para la sucursal verde
- si querés importar repuestos para naranja, cambiá temporalmente `DB_NAME=setup_naranja`

Si querés más adelante, puedo dejarte un importador que reciba la sucursal por parámetro para no tocar el `.env`.

## 2. Subir los Excel

Subí estos archivos dentro de:

`/var/www/sput/setup_import/`

Archivos esperados:

- `clientes otro.xlsx`
- `articulos.xlsx`

## 3. Ejecutar importación de clientes

```bash
cd /var/www/sput
source .venv/bin/activate
python setup_import/importar_clientes_setup.py
```

Esto actualiza la tabla `clientes` compartida.

## 4. Ejecutar importación de repuestos para sucursal verde

Con `.env` apuntando a:

```env
DB_NAME=setup
```

ejecutá:

```bash
cd /var/www/sput
source .venv/bin/activate
python setup_import/importar_repuestos_setup.py
```

## 5. Ejecutar importación de repuestos para sucursal naranja

Hacé backup del `.env`:

```bash
cd /var/www/sput
cp .env .env.backup
```

Cambiá temporalmente:

```env
DB_NAME=setup_naranja
```

Ejecutá:

```bash
cd /var/www/sput
source .venv/bin/activate
python setup_import/importar_repuestos_setup.py
```

Y después restaurá:

```bash
mv .env.backup .env
sudo systemctl restart sput
```

## 6. Recomendación segura antes de importar

Antes de correr cualquiera de los imports:

```bash
mysqldump -u setup_user -p setup > /tmp/setup_antes_import.sql
mysqldump -u setup_user -p setup_naranja > /tmp/setup_naranja_antes_import.sql
```

## 7. Orden sugerido para actualización productiva

1. Backup de `setup` y `setup_naranja`
2. Subir Excel a `setup_import/`
3. Importar clientes
4. Importar repuestos de verde
5. Importar repuestos de naranja si corresponde
6. Reiniciar servicio
7. Verificar desde la app

## 8. Qué hace cada script

### `importar_clientes_setup.py`

- lee `setup_import/clientes otro.xlsx`
- inserta o actualiza clientes por `id`
- actualiza datos generales de cliente

### `importar_repuestos_setup.py`

- lee `setup_import/articulos.xlsx`
- inserta o actualiza repuestos por `id`
- actualiza nombre, descripción y costo

