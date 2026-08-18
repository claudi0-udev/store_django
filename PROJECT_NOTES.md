# Notas del proyecto - store_django

> [!IMPORTANT]
> **Regla de Desarrollo de Git**: Todos los cambios, nuevas funcionalidades, pruebas, commits y pushes deben realizarse **SIEMPRE en la rama `testing`**. La rama `master` o `main` solo se actualiza cuando el usuario lo solicite explícitamente.

## Contexto general
- Proyecto Django de tienda con la app `showcase`.

- El objetivo principal ha sido convertirlo en una base más realista y mantenible, con validaciones, datos de ejemplo, autenticación y una experiencia de inicio más completa.

## Cambios implementados
- Se fortalecieron las validaciones de productos y entidades del catálogo para evitar datos incompletos o inválidos.
- Los campos monetarios (`price`, `msrp`) se cambiaron a `DecimalField` para manejar valores con precisión de céntimos.
- Se añadieron datos de ejemplo realistas con un comando de gestión para poblar la base de datos.
- Se incorporó autenticación con login, logout, registro y control de acceso para vistas administrativas.
- La ruta pública de registro ahora crea únicamente cuentas de cliente (`customer`).
  - Las cuentas `staff`, `admin` o `superuser` solo pueden crearse desde el admin de Django o mediante un superuser autorizado.
- Se creó una landing page para visitantes con:
  - hero banner
  - carrusel de promociones
  - sección de mejores ventas
  - bloque de nuevos productos
  - buscador avanzado con filtros por categoría y orden
- Se añadió un flujo de creación de productos con formulario dedicado, soporte de carga de imágenes y mensajes de feedback.
- Se configuró el manejo de archivos multimedia (`MEDIA_URL` y `MEDIA_ROOT`) en `settings.py` y `urls.py`.
- Se corrigió la estructura HTML de las plantillas (`product_detail.html` y `products_list.html`) para evitar etiquetas anidadas duplicadas.
- Se implementó el módulo de Carrito de Compras (Shopping Cart):
  - Servicio `Cart` basado en sesiones de Django (`request.session`).
  - Context processor global para mostrar el contador de ítems en el navbar.
  - Vistas de detalle, adición con cantidad, actualización (+ / -), eliminación y vaciado.
  - Plantilla `cart_detail.html` con tabla de productos, selector de cantidad interactivo y resumen de compra.
  - Botones de "Añadir al carrito" integrados en el detalle de producto, listado y landing page.
- Se implementó el módulo de Checkout y Órdenes de Compra:
  - Modelos `Order` y `OrderItem` para persistencia histórica de transacciones y estados.
  - Panel de administración `OrderAdmin` con vista `OrderItemInline`.
  - Formulario de despacho `OrderCreateForm` con validaciones de contacto y dirección.
  - Vistas de Checkout (`orderCreate`), Confirmación de compra (`orderConfirmation`) e Historial de pedidos (`orderHistory`).
  - Descuento automático de stock de inventario tras la confirmación de la orden.
  - Vaciado automático del carrito de sesión al completar el pedido.
- Se implementó la Gestión Administrativa de Productos (CRUD Completo):
  - Vista y plantilla de edición (`EditProduct` y `edit_product.html`) con prellenado de campos, reemplazo de imágenes y actualización de atributos dinámicos (`FeatureValue`).
  - Vista y plantilla de eliminación con **Borrado Lógico (Soft Delete)** y **Auditoría de Respaldos (`ProductAuditLog`)**:
    - Al retirar un producto, se almacena un snapshot JSON con todos sus campos históricos y fecha/usuario de eliminación.
    - Se marca `is_active=False` y `deleted_at=timezone.now()`.
    - Deja de mostrarse en la tienda pública, pero mantiene el historial de compras en `OrderItem` intacto (`on_delete=models.SET_NULL`).
    - Vista de gestión de papelera (`ArchivedProductsList` y `archived_products.html`) con función de **restauración en un solo clic** (`RestoreProduct`).
  - Barra de herramientas administrativa en la vista de detalle de producto (`product_detail.html`) y accesos rápidos en la tabla de productos (`products_list.html`).
- Se rediseñó y optimizó la Autenticación y Registro de Usuarios:
  - Formulario de Registro `UserRegistrationForm`: Solicita nombre, apellido, correo electrónico obligatorio, usuario, contraseña y confirmación con validación de unicidad y contraseñas coincidentes.
  - Formulario de Inicio de Sesión `UserLoginForm`: Estilizado con Bootstrap, placeholders y mensajes de error en español.
  - Rediseño visual de las plantillas `login.html`, `register.html` y `logged_out.html` en tarjetas limpias, centradas y responsive.
  - Redirección automática de usuarios ya autenticados al intentar ingresar a `/accounts/login/` o `/accounts/register/`.
  - Soporte de parámetro `next` para continuar el flujo de compra/checkout tras autenticarse.
- Se implementó el Sistema de Notificación y Confirmación de Pedidos por Correo Electrónico:
  - Módulo `showcase/emails.py` con la función `send_order_confirmation_email(order)`.
  - Plantillas de correo responsivas en HTML (`order_confirmation_email.html`) y formato texto plano (`order_confirmation_email.txt`).
  - Envío automático de resumen de compra, productos, subtotales, total y dirección de despacho al email del comprador al completar el checkout.
  - Configuración de `EMAIL_BACKEND` y `DEFAULT_FROM_EMAIL` en `mysite/settings.py`.
- Se implementó la Selección de Punto Exacto de Entrega con Mapa Interactivo (Leaflet.js + OpenStreetMap):
  - Mapa interactivo en Checkout (`order_create.html`):
    - Al hacer clic o arrastrar el pin en el mapa, se realiza geocodificación inversa inmediata con Nominatim y **se escribe automáticamente el nombre de la calle, número, comuna y código postal en la casilla de texto**.
    - La casilla de texto de dirección es **100% editable por el usuario** (para complementar con piso, departamento, torre, etc.).
    - Las coordenadas geográficas exactas (`latitude`, `longitude`) del pin se guardan en la base de datos vinculadas a la compra.
    - Botón *"🎯 Mi ubicación actual"* para autodetectar GPS con un solo clic.
    - Botón *"🔍 Ubicar en mapa"* para geocodificar la dirección tipeada.
    - Almacenamiento de coordenadas exactas en el modelo `Order` (migración `0015_order_latitude_order_longitude.py`).
  - Panel de Despacho para el Administrador / Repartidor (`manage_order_detail.html`):
    - Visualización del mapa con el pin exacto de entrega del cliente.
    - Botones de navegación instantánea *"🗺️ Google Maps"* y *"🚗 Waze"* con coordenadas GPS directas.

- Se implementó el Panel Administrativo de Gestión y Despacho de Pedidos:

  - Vista general `ManageOrdersList` (`/manage/orders/`):
    - Métricas en tiempo real: total de pedidos, pendientes, pagados/por preparar, en camino, entregados y recaudación total.
    - Filtros por estado (*Pendiente*, *Pagada*, *Enviada*, *Completada*, *Cancelada*).
    - Buscador universal por ID de orden, nombre de cliente, teléfono, email o código de seguimiento.
  - Vista de detalle operativo `ManageOrderDetail` (`/manage/orders/<id>/`):
    - Ficha completa del cliente con acceso telefónico directo (`tel:` y llamada rápida) y dirección de despacho.
    - Formulario de actualización de estado y verificación de pagos.
    - Asignación de empresa de transporte (Courier) y número de seguimiento (*Tracking ID*).
    - Campo de notas internas de despacho y entrega.
    - Botón para imprimir hoja de despacho / empaque (`window.print()`).
  - Visibilidad de seguimiento para el comprador en "Mis pedidos" y en el detalle de compra.
  - Compatibilidad retroactiva: Permite actualizar y despachar órdenes antiguas creadas antes de la obligatoriedad del teléfono, con la opción de que el staff ingrese el teléfono si lo obtiene posteriormente.
  - Campos agregados al modelo `Order`: `tracking_company`, `tracking_number` y `notes` (migraciones `0013_...` y `0014_alter_order_phone.py`).
- Se documentó la configuración básica del proyecto y los usuarios por defecto en el README.

## Archivos clave
- `showcase/templates/manage_orders.html`: panel de control y despacho de pedidos.
- `showcase/templates/manage_order_detail.html`: ficha de gestión y actualización de estado de una orden.
- `showcase/emails.py`: servicio de envío de correos de pedidos y notificaciones.
- `showcase/templates/emails/order_confirmation_email.html`: plantilla HTML de confirmación de compra.
- `showcase/templates/emails/order_confirmation_email.txt`: plantilla en texto plano para correos.
- `showcase/forms.py`: `ProductForm`, `OrderCreateForm`, `UserRegistrationForm` y `UserLoginForm`.
- `showcase/models.py`: modelos de catálogo, atributos dinámicos, `Order`, `OrderItem`, `Product` y `ProductAuditLog`.
- `showcase/cart.py`: clase `Cart` que gestiona la lógica y cálculos del carrito en sesión.
- `showcase/context_processors.py`: inyector del carrito para renderizado global en plantillas.
- `showcase/views.py`: control de catálogo, CRUD de productos, soft delete, registro, autenticación, gestión de pedidos, checkout y live search.
- `showcase/templates/registration/login.html`: interfaz moderna de inicio de sesión.
- `showcase/templates/register.html`: interfaz completa de creación de cuenta.
- `showcase/templates/registration/logged_out.html`: pantalla de despedida / cierre de sesión.
- `showcase/templates/edit_product.html`: formulario de edición de productos.
- `showcase/templates/delete_product_confirm.html`: diálogo de confirmación de eliminación lógica.
- `showcase/templates/archived_products.html`: panel de productos archivados y registro de auditoría de respaldos.
- `showcase/templates/cart_detail.html`: carrito de compras con actualización dinámica AJAX, selector de cantidad y banner de envío gratis.
- `showcase/templates/order_create.html`: checkout con stepper, autollenado de dirección habitual (1 clic) y selector de punto en mapa interactivo.
- `showcase/templates/order_confirmation.html`: comprobante con tracking timeline visual, enlace a WhatsApp e impresión de recibo.
- `showcase/templates/order_history.html`: panel de historial de pedidos con stepper gráfico de avance del despacho y soporte directo.
- `showcase/templates/base_layout.html`: layout base con live search predictivo en navbar, toasts de adición al carrito y badge reactivo.

## Estado actual
- Suite de Experiencia del Comprador (UI/UX) 100% implementada y verificada:
  1. Live Search con autocompletado en navbar.
  2. Compra rápida desde tarjetas con toasts flotantes y badges de urgencia/stock.
  3. Ficha de producto con selector `+`/`-`, cuotas, sellos y módulo de Cross-selling.
  4. Carrito dinámico con reactividad AJAX sin recargas de página.
  5. Checkout inteligente con autocompletado de dirección previa en 1 clic.
  6. Post-venta con línea de tiempo gráfica de despacho y asistencia directa por WhatsApp.
- La app pasa todas las comprobaciones de Django y la suite de pruebas unitarias (`41/41 tests OK`).
- Servidor de desarrollo activo en `http://127.0.0.1:8000/`.

## Próximos pasos sugeridos
- Permitir la personalización de temas y colores de la tienda (Store Branding / Settings).
- Integración directa con pasarela de pagos en línea externa (Webpay Plus / Mercado Pago / Stripe).












