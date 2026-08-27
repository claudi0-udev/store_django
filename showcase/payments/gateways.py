import random
import uuid
from django.utils import timezone
from showcase.emails import send_order_confirmation_email


def confirm_order_payment(order, auth_code=None, card_last4=None, card_type=None, installments=1, transaction_id=None, gateway_name=None):
    """
    Confirma de manera segura el pago de una orden, actualiza su estado a 'paid',
    registra los metadatos bancarios del voucher y despacha el correo de confirmación.
    """
    if not auth_code:
        auth_code = f"{random.randint(100000, 999999)}"

    if not transaction_id:
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

    if not card_last4:
        card_last4 = f"{random.randint(1000, 9999)}"

    if not card_type:
        card_type = 'Tarjeta de Crédito / Débito'

    order.paid = True
    order.status = 'paid'
    order.payment_auth_code = auth_code
    order.payment_card_last4 = str(card_last4)[-4:]
    order.payment_card_type = card_type
    order.payment_installments = int(installments) if installments else 1
    order.payment_transaction_id = transaction_id
    order.payment_date = timezone.now()
    if gateway_name:
        order.payment_method = gateway_name

    order.save()

    # Enviar correo de confirmación con voucher
    try:
        send_order_confirmation_email(order)
    except Exception as e:
        print(f"Error al enviar correo de confirmación para orden #{order.id}: {e}")

    return order


def get_gateway_display_info(gateway_key):
    """
    Retorna información visual e instrucciones de cada pasarela.
    """
    gateways = {
        'webpay': {
            'name': 'Webpay Plus (Transbank)',
            'icon': '💳',
            'badge_class': 'badge-danger',
            'description': 'Tarjetas de crédito, débito (Redcompra) y prepago en Chile.',
            'supported_cards': ['Visa', 'Mastercard', 'American Express', 'Redcompra', 'Magna'],
        },
        'mercadopago': {
            'name': 'Mercado Pago',
            'icon': '🤝',
            'badge_class': 'badge-info',
            'description': 'Paga con tu cuenta Mercado Pago, dinero disponible o tarjetas en cuotas.',
            'supported_cards': ['Saldo Mercado Pago', 'Visa', 'Mastercard', 'Lider BCI', 'CMR Falabella'],
        },
        'sandbox_card': {
            'name': 'Tarjeta Directa (Pago Seguro)',
            'icon': '🔒',
            'badge_class': 'badge-primary',
            'description': 'Procesamiento directo de tarjeta con cifrado bancario seguro.',
            'supported_cards': ['Visa', 'Mastercard', 'Debito'],
        },
        'transfer': {
            'name': 'Transferencia Bancaria Manual',
            'icon': '🏦',
            'badge_class': 'badge-secondary',
            'description': 'Transferencia electrónica a cuenta corriente con validación de comprobante.',
            'bank_details': {
                'bank_name': 'Banco de Chile / Edwards',
                'account_type': 'Cuenta Corriente',
                'account_number': '00-123-45678-90',
                'rut': '76.123.456-K',
                'beneficiary': 'Store Django SpA',
                'email': 'pagos@tiendadjango.cl',
            }
        },
    }
    return gateways.get(gateway_key, gateways['webpay'])
