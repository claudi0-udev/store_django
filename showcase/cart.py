from decimal import Decimal
from .models import Product, ProductVariant

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

    def _get_item_key(self, product, variant=None):
        product_id = getattr(product, 'id', product)
        variant_id = getattr(variant, 'id', variant) if variant else None
        if variant_id:
            return f"{product_id}:{variant_id}"
        return str(product_id)

    def add(self, product, quantity=1, override_quantity=False, variant=None):
        item_key = self._get_item_key(product, variant)
        variant_id = getattr(variant, 'id', variant) if variant else None

        if variant:
            item_price = str(variant.get_price())
            available_stock = variant.units if variant.units > 0 else 999999
        else:
            item_price = str(product.price)
            available_stock = product.units if product.units > 0 else 999999

        if item_key not in self.cart:
            self.cart[item_key] = {
                'quantity': 0,
                'price': item_price,
                'product_id': product.id,
                'variant_id': variant_id,
            }

        if override_quantity:
            target_quantity = max(1, min(quantity, available_stock))
            self.cart[item_key]['quantity'] = target_quantity
        else:
            current_quantity = self.cart[item_key]['quantity']
            target_quantity = min(current_quantity + quantity, available_stock)
            self.cart[item_key]['quantity'] = target_quantity

        self.cart[item_key]['price'] = item_price
        self.cart[item_key]['product_id'] = product.id
        self.cart[item_key]['variant_id'] = variant_id
        self.save()

    def decrement(self, product, variant=None, item_key=None):
        if not item_key:
            item_key = self._get_item_key(product, variant)
            if item_key not in self.cart and str(getattr(product, 'id', product)) in self.cart:
                item_key = str(getattr(product, 'id', product))

        if item_key in self.cart:
            if self.cart[item_key]['quantity'] > 1:
                self.cart[item_key]['quantity'] -= 1
            else:
                del self.cart[item_key]
            self.save()

    def remove(self, product=None, variant=None, item_key=None):
        if item_key and item_key in self.cart:
            del self.cart[item_key]
            self.save()
            return

        if product is not None:
            key = self._get_item_key(product, variant)
            if key in self.cart:
                del self.cart[key]
                self.save()
            elif str(getattr(product, 'id', product)) in self.cart:
                del self.cart[str(getattr(product, 'id', product))]
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
        cart_copy = {k: v.copy() for k, v in self.cart.items()}
        product_ids = set()
        variant_ids = set()

        for k, item in cart_copy.items():
            p_id = item.get('product_id')
            if not p_id:
                try:
                    p_id = int(str(k).split(':')[0])
                except Exception:
                    continue
            product_ids.add(p_id)

            v_id = item.get('variant_id')
            if not v_id and ':' in str(k):
                try:
                    v_id = int(str(k).split(':')[1])
                except Exception:
                    pass
            if v_id:
                variant_ids.add(v_id)

        products = {p.id: p for p in Product.objects.filter(id__in=product_ids).select_related('category', 'brand')}
        variants = {v.id: v for v in ProductVariant.objects.filter(id__in=variant_ids)} if variant_ids else {}

        for item_key, item in cart_copy.items():
            p_id = item.get('product_id')
            if not p_id:
                try:
                    p_id = int(str(item_key).split(':')[0])
                except Exception:
                    continue
            product = products.get(p_id)
            if not product:
                continue

            v_id = item.get('variant_id')
            if not v_id and ':' in str(item_key):
                try:
                    v_id = int(str(item_key).split(':')[1])
                except Exception:
                    pass
            variant = variants.get(v_id) if v_id else None

            item['item_key'] = item_key
            item['product'] = product
            item['variant'] = variant
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


