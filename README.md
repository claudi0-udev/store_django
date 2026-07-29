# Store Django

Proyecto Django para una plantilla base de tienda online, con gestión inicial de productos, categorías, marcas, fabricantes, distribuidores y características. El objetivo es servir como base reutilizable para distintos tipos de ecommerce.

## Requisitos

- Python 3.10 o superior
- pip
- virtualenv (opcional, pero recomendado)

## 1. Clonar el proyecto

```bash
git clone <url-del-repositorio>
cd store_django
```

## 2. Crear y activar un entorno virtual

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows (PowerShell)

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 4. Preparar la base de datos

Este proyecto está configurado para usar SQLite por defecto en desarrollo, por lo que no necesitas una base de datos externa.

Ejecuta:

```bash
python manage.py migrate
```

## 5. Crear un superusuario (opcional)

```bash
python manage.py createsuperuser
```

## 6. Crear usuarios por defecto para desarrollo

Puedes crear usuarios de ejemplo para los roles más comunes con:

```bash
python manage.py create_default_users
```

Credenciales creadas:

- `admin` / `Admin$2026!` — superusuario staff
- `staff` / `Staff$2026!` — usuario staff sin superuser
- `customer` / `Customer$2026!` — usuario regular

## 7. Ejecutar la aplicación

```bash
python manage.py runserver
```

Abre en tu navegador:

```text
http://127.0.0.1:8000/products/
```

## Estructura general

- `mysite/`: configuración principal de Django
- `showcase/`: aplicación principal con modelos, vistas, plantillas y URLs
- `requirements.txt`: dependencias del proyecto

## Nota sobre la base de datos

La configuración actual usa SQLite para desarrollo local. Si deseas usar PostgreSQL, puedes cambiar la configuración en `mysite/settings.py` y ajustar los datos de conexión.

### Credenciales por defecto

- En modo SQLite no hay usuario Django preconfigurado.
- Para crear un administrador usa:

```bash
python manage.py createsuperuser
```

- Si configuras PostgreSQL cambiando `USE_SQLITE` a `0`, los valores por defecto en `mysite/settings.py` son:
  - `NAME`: `store`
  - `USER`: `pi`
  - `PASSWORD`: `1234`
  - `HOST`: `192.168.1.190`
  - `PORT`: `5432`

## Problemas comunes

### Error: `ModuleNotFoundError: No module named 'django'`

Asegúrate de haber activado el entorno virtual y ejecutado:

```bash
pip install -r requirements.txt
```

### Error al levantar el servidor por configuración de base de datos

Si usas SQLite, asegúrate de ejecutar:

```bash
python manage.py migrate
```

## Siguiente paso recomendado

- Crear el módulo de carrito de compras
- Añadir autenticación de usuarios
- Implementar catálogo más dinámico y personalizable
