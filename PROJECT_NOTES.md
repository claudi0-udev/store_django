# Notas del proyecto - store_django

## Contexto general
- Proyecto Django de tienda (`store_django`) con app `showcase`.
- Se estaba trabajando en mejorar validaciones, manejar precios como `DecimalField`, sembrar datos de ejemplo y proteger rutas de administración con autenticación.
- Se implementó una interfaz básica de registro/login, y se agregó control de acceso para vistas administrativas.

## Cambios recientes
- `showcase/models.py`: Campos de precio (`price`, `msrp`) convertidos a `DecimalField(max_digits=10, decimal_places=2)`.
- `showcase/views.py`: se agregó validación de datos y se corrigió protección de la vista `Register` retirando `@staff_required`.
- `showcase/urls.py`: se añadió la ruta `accounts/register/` para el registro de usuarios.
- `mysite/urls.py`: se mantiene `accounts/` incluido con `django.contrib.auth.urls`.
- Verificación: `python manage.py check` pasó sin errores y `reverse('register')` resuelve correctamente.

## Estado actual
- La ruta de registro es accesible para usuarios no staff.
- Las vistas de administración siguen restringidas por `@staff_required`.
- La configuración de autenticación y las plantillas de registro/login están integradas.

## Próximos pasos sugeridos
- Revisar `showcase/templates/` para asegurar que el menú muestre correctamente opciones de login/logout y registro.
- Añadir pruebas de flujo de registro y acceso de usuarios no staff.
- Extender permisos para roles adicionales si se necesita control más fino de administración.
