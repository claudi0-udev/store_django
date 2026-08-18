import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_order_confirmation_email(order):
    """
    Envía un correo de confirmación de pedido con formato HTML y versión en texto plano.
    """
    if not order or not order.email:
        return False

    subject = f"¡Confirmación de Pedido #{order.id}! - Tienda Django"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@tiendadjango.cl')
    to = [order.email]

    context = {
        'order': order,
        'items': order.items.select_related('product').all(),
    }

    try:
        text_content = render_to_string('emails/order_confirmation_email.txt', context)
        html_content = render_to_string('emails/order_confirmation_email.html', context)

        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Error al enviar correo de confirmación para orden #{order.id}: {e}")
        return False
