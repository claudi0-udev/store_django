# Notas del proyecto - store_django

## Contexto general
- Proyecto Django de tienda en fase de prototipo/mi-ecommerce con la app `showcase`.
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
- Se añadió un flujo de creación de productos con formulario dedicado y mensajes de feedback.
- Se documentó la configuración básica del proyecto y los usuarios por defecto en el README.

## Archivos clave
- `showcase/models.py`: modelo de productos y catálogo con validaciones y campos monetarios seguros.
- `showcase/forms.py`: formulario dedicado para crear productos.
- `showcase/views.py`: control de vistas públicas, administración y autenticación.
- `showcase/templates/home.html`: landing page con secciones de ecommerce.
- `showcase/templates/add_product.html`: formulario de alta de productos.
- `showcase/management/commands/`: comandos para sembrar datos y crear usuarios por defecto.

## Estado actual
- El proyecto está estable y funcional.
- La app pasa las comprobaciones de Django y las pruebas del proyecto.
- La experiencia de inicio ya es mucho más cercana a una tienda online real.

## Próximos pasos sugeridos
- Pulir el diseño visual de la interfaz.
- Añadir acciones de compra/cart y detalle de producto más rico.
- Mejorar la navegación por categorías y filtros.
- Extender pruebas de autenticación y flujos de usuario.
