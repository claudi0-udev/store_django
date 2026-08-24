from .cart import Cart
from .models import StoreSettings


def cart(request):
    """Inyecta el objeto Cart en todas las plantillas HTML."""
    return {'cart': Cart(request)}


def store_settings_processor(request):
    """Inyecta la configuración global de la tienda (logo, nombre, banners) en todas las plantillas."""
    return {
        'store_settings': StoreSettings.get_solo()
    }
