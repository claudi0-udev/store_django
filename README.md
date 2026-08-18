# 🛒 Store Django - Plataforma de Comercio Electrónico

Plataforma de comercio electrónico moderna, robusta y escalable desarrollada en **Django 6.1** y **Python 3**. Diseñada como base reutilizable y profesional para tiendas en línea, con catálogo dinámico, carrito de compras en sesión, checkout con geolocalización en mapa interactivo, sistema de correos de confirmación, panel de despacho para administradores y borrado lógico con auditoría.

---

## 🚀 Características Principales

### 📦 1. Catálogo y Gestión de Productos
- Catálogo interactivo con filtrado y búsqueda.
- Subida y almacenamiento de imágenes con **Pillow** (`media/product_images/`).
- Manejo exacto de precios monetarios (`DecimalField`).
- Gestión de marcas, categorías, fabricantes, distribuidores y características dinámicas clave-valor.
- Formularios de creación y edición con validación de inventario (`units`) y datos normalizados.

### 🛡️ 2. Borrado Lógico y Auditoría (Soft Delete)
- Al eliminar un producto, no se destruye de la base de datos: se marca como inactivo (`is_active=False`) y se registra la fecha (`deleted_at`).
- **Respaldo de Auditoría:** Cada eliminación genera un snapshot en formato JSON en `ProductAuditLog`.
- **Integridad de Pedidos:** Los pedidos históricos mantienen intacto su registro monetario y nombre de producto sin errores en cascada (`SET_NULL`).
- **Papelera de Reciclaje:** Panel en `/products/archived/` para restaurar productos archivados en 1 clic.

### 🛒 3. Carrito de Compras en Sesión
- Arquitectura desacoplada en `showcase/cart.py` mediante sesiones de Django.
- Agregar productos, ajustar cantidades, eliminar artículos individuales o vaciar el carrito.
- Contador dinámico en la barra de navegación visible en todas las páginas vía `context_processors.py`.
- Descuento automático de stock al finalizar la compra.

### 🗺️ 4. Checkout con Mapa Interactivo y Geolocalización GPS Completa
- **Leaflet.js + OpenStreetMap:** Mapa interactivo integrado sin necesidad de API keys de pago.
- **Pin Arrastrable y Clic:** Selección del punto exacto de entrega con marcador interactivo y botón *"🎯 Mi ubicación actual"*.
- **Autocompletado Estructurado (*Reverse Geocoding*):** Al mover el pin o hacer clic en el mapa, el sistema obtiene automáticamente y rellena de forma editable:
  - **Dirección (Calle y número)**
  - **Comuna / Ciudad**
  - **Región / Estado**
  - **País**
  - **Código Postal**
- **Casillas de Texto Editables:** El comprador puede complementar libremente su dirección (depto, torre, piso o villa).
- **Seguridad en Contacto:** Teléfono de contacto obligatorio con validación numérica ($\ge 8$ dígitos).
- **Almacenamiento de Coordenadas:** Las coordenadas GPS (`latitude`, `longitude`) quedan guardadas en la orden y vinculadas a Google Maps y Waze.


### 📧 5. Sistema de Confirmación por Correo Electrónico
- Envío automático de correo al comprador al completar la orden.
- Plantilla HTML responsiva moderna (`order_confirmation_email.html`) y formato alternativo en texto plano (`order_confirmation_email.txt`).
- Desglose de artículos, precios unitarios, total pagado, dirección y teléfono de entrega.

### 🚚 6. Panel de Gestión y Despacho de Pedidos (Staff / Admin)
- Vista centralizada en `/manage/orders/` para el equipo de logística y operaciones.
- **Métricas en tiempo real:** Total de órdenes, pedidos pendientes, pagados/en preparación, en camino, entregados y recaudación total.
- **Filtros por Estado:** Pestañas para filtrar por *Pendiente*, *Pagada*, *En Camino*, *Completada* o *Cancelada*.
- **Buscador:** Búsqueda por número de pedido, cliente, teléfono, email o código de seguimiento.
- **Acciones Rápidas:**
  - Llamada directa al cliente mediante enlace `tel:`.
  - Asignación de Courier (*Chilexpress, Starken, Blue Express, etc.*) y número de seguimiento (*Tracking ID*).
  - Visualización del mapa con el pin exacto de entrega y botones directos hacia **Google Maps** y **Waze**.
  - Impresión directa de hoja de despacho y empaque (`🖨️`).

### ✨ 7. Suite de Experiencia del Comprador (UI/UX)
- **Live Search Autocomplete:** Búsqueda predictiva instantánea en la barra de navegación con imágenes, categorías, stock y precios.
- **Compra Rápida desde Tarjetas:** Botón `+ 🛒` directo en la página principal y catálogo con notificación flotante (*Toast*) y animación.
- **Badges de Stock y Urgencia:** Alertas visuales dinámicas (*"🔥 ¡Últimas X unidades!"*, *"En Stock"*, *"Agotado"*).
- **Ficha de Producto Completa:** Selector táctil `+`/`-`, facilidades en cuotas con tarjeta, sellos de garantía y módulo de productos relacionados (*Cross-Selling*).
- **Carrito Dinámico AJAX:** Actualización de cantidades y totales en tiempo real sin recargar la página y banner de envío gratis.
- **Checkout con Memoria de Dirección:** *Stepper* de progreso (`Carrito` ➔ `Despacho` ➔ `Confirmación`) y botón para reutilizar la dirección anterior en 1 clic.
- **Seguimiento Visual y WhatsApp:** Línea de tiempo gráfica de despacho (*Tracking Timeline*) y botón de soporte directo por WhatsApp con el número de orden precargado.


### 👤 8. Autenticación y Cuentas de Usuario
- **Registro de Clientes:** Formulario completo con validación de nombre, apellido, email único y contraseña segura.
- **Inicio de Sesión:** Interfaz moderna con selector de credenciales de prueba preconfiguradas.
- **Historial de Pedidos:** Sección "Mis pedidos" para que los clientes consulten el estado de sus compras y su código de seguimiento.


---

## 🛠️ Requisitos e Instalación

### Requisitos Previos
- **Python 3.10** o superior
- **pip** y **git**

### 1. Clonar el repositorio y acceder
```bash
git clone https://github.com/claudi0-udev/store_django.git
cd store_django
git checkout testing
```

### 2. Crear y activar el entorno virtual

**En Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**En Windows (PowerShell):**
```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Aplicar migraciones de la base de datos
```bash
python manage.py migrate
```

### 5. Cargar usuarios por defecto (Desarrollo)
```bash
python manage.py create_default_users
```

---

## 👥 Credenciales de Acceso por Defecto

| Rol | Usuario | Contraseña | Permisos |
| :--- | :--- | :--- | :--- |
| **Super Administrador** | `admin` | `Admin$2026!` | Acceso total a Django Admin, catálogo, despacho y papelera |
| **Personal Staff / Despacho** | `staff` | `Staff$2026!` | Gestión de catálogo, panel de despacho y auditoría |
| **Cliente Regular** | `customer` | `Customer$2026!` | Catálogo, carrito, checkout e historial de compras |

---

## 🌐 Ejecución del Servidor

Inicia el servidor de desarrollo:
```bash
python manage.py runserver 0.0.0.0:8000
```

Accede desde tu navegador:
* **Inicio de la Tienda:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Catálogo de Productos:** [http://127.0.0.1:8000/products/](http://127.0.0.1:8000/products/)
* **Carrito de Compras:** [http://127.0.0.1:8000/cart/](http://127.0.0.1:8000/cart/)
* **Panel de Gestión de Pedidos (Staff):** [http://127.0.0.1:8000/manage/orders/](http://127.0.0.1:8000/manage/orders/)
* **Papelera y Auditoría de Productos:** [http://127.0.0.1:8000/products/archived/](http://127.0.0.1:8000/products/archived/)
* **Panel Django Admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con una completa suite de pruebas automatizadas que cubren modelos, formularios, vistas, soft delete, flujo de compras, validación telefónica, coordenadas GPS y envío de correos.

Para ejecutar todas las pruebas:
```bash
python manage.py test
```

**Resultado actual:**
```text
Ran 36 tests in 58.052s

OK
```

---

## 📂 Estructura del Proyecto

```text
store_django/
├── mysite/                   # Configuración del proyecto Django
│   ├── settings.py           # Ajustes generales, media, emails y bases de datos
│   ├── urls.py               # Ruteo principal y autenticación
│   └── wsgi.py
├── showcase/                 # Aplicación principal de la tienda
│   ├── models.py             # Modelos: Product, Order, OrderItem, ProductAuditLog, etc.
│   ├── views.py              # Controladores de catálogo, carrito, checkout y gestión
│   ├── forms.py              # Formularios: ProductForm, OrderCreateForm, Registro y Login
│   ├── cart.py               # Servicio de lógica del carrito en sesión
│   ├── emails.py             # Servicio de despacho de correos de confirmación
│   ├── context_processors.py # Inyección global del carrito en plantillas
│   ├── admin.py              # Configuración de Django Admin y acciones bulk
│   ├── urls.py               # Rutas de la tienda y panel de despacho
│   ├── tests.py              # Suite de 36 pruebas unitarias e integración
│   └── templates/            # Plantillas HTML responsivas (Bootstrap 4 + Leaflet)
│       ├── base_layout.html
│       ├── home.html
│       ├── products_list.html
│       ├── product_detail.html
│       ├── edit_product.html
│       ├── archived_products.html
│       ├── cart_detail.html
│       ├── order_create.html # Checkout con mapa interactivo
│       ├── order_confirmation.html
│       ├── order_history.html
│       ├── manage_orders.html       # Tablero de despacho para staff
│       ├── manage_order_detail.html # Ficha operativa con mapa y tracking
│       ├── registration/
│       │   ├── login.html
│       │   └── logged_out.html
│       └── emails/
│           ├── order_confirmation_email.html
│           └── order_confirmation_email.txt
├── media/                    # Almacenamiento de imágenes de productos
├── requirements.txt          # Dependencias de Python (Django, Pillow, etc.)
└── README.md                 # Documentación completa del proyecto
```
