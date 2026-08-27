from decimal import Decimal
from .models import Product

CART_SESSION_ID = 'cart'


class Cart:
    def __init__(self, request):
        self.session = getattr(request, 'session', None)
        if self.session is None:
            self.cart = {}
            return

        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.price),
            }

        available_stock = product.units if product.units > 0 else 999999

        if override_quantity:
            target_quantity = max(1, min(quantity, available_stock))
            self.cart[product_id]['quantity'] = target_quantity
        else:
            current_quantity = self.cart[product_id]['quantity']
            target_quantity = min(current_quantity + quantity, available_stock)
            self.cart[product_id]['quantity'] = target_quantity

        self.cart[product_id]['price'] = str(product.price)
        self.save()

    def decrement(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            if self.cart[product_id]['quantity'] > 1:
                self.cart[product_id]['quantity'] -= 1
            else:
                del self.cart[product_id]
            self.save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        self.cart = {}
        if self.session is not None and CART_SESSION_ID in self.session:
            self.session[CART_SESSION_ID] = {}
        self.remove_coupon()
        self.save()

    def save(self):
        if self.session is not None and hasattr(self.session, 'modified'):
            self.session.modified = True

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids).select_related('category', 'brand')
        cart_copy = {k: v.copy() for k, v in self.cart.items()}

        for product in products:
            item = cart_copy[str(product.id)]
            item['product'] = product
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum((Decimal(item['price']) * item['quantity'] for item in self.cart.values()), Decimal('0.00'))

    def get_total_quantity(self):
        return sum(item['quantity'] for item in self.cart.values())

    @property
    def coupon_id(self):
        if self.session is not None:
            return self.session.get('coupon_id')
        return None

    def get_coupon(self):
        if self.coupon_id:
            from .models import Coupon
            try:
                coupon = Coupon.objects.get(id=self.coupon_id, is_active=True)
                valid, _ = coupon.is_valid(self.get_total_price())
                if valid:
                    return coupon
                else:
                    self.remove_coupon()
            except Coupon.DoesNotExist:
                self.remove_coupon()
        return None

    def apply_coupon(self, coupon_code):
        from .models import Coupon
        code = (coupon_code or '').strip().upper()
        if not code:
            return False, "Por favor ingresa un código de cupón."
        try:
            coupon = Coupon.objects.get(code=code)
            valid, msg = coupon.is_valid(self.get_total_price())
            if not valid:
                return False, msg
            if self.session is not None:
                self.session['coupon_id'] = coupon.id
                self.save()
            return True, f"¡Cupón '{coupon.code}' aplicado con éxito!"
        except Coupon.DoesNotExist:
            return False, f"El código de cupón '{code}' no existe."

    def remove_coupon(self):
        if self.session is not None and 'coupon_id' in self.session:
            del self.session['coupon_id']
            self.save()

    def get_discount(self):
        coupon = self.get_coupon()
        if coupon:
            return coupon.calculate_discount(self.get_total_price())
        return Decimal('0.00')

    def get_total_price_after_discount(self):
        return max(Decimal('0.00'), self.get_total_price() - self.get_discount())


