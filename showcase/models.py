from decimal import Decimal
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinLengthValidator, MinValueValidator

from django.db import models
from django.utils import timezone





def _normalize_name(value):
    return (value or '').strip()


class Category(models.Model):
    name = models.CharField(max_length=200, validators=[MinLengthValidator(2)])
    parent_category_id = models.IntegerField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0, verbose_name='Conteo de visitas')


    def clean(self):
        # Normalize category names so blanks and extra spaces are rejected consistently.
        super().clean()
        self.name = _normalize_name(self.name)
        if not self.name:
            raise ValidationError({'name': 'El nombre de la categoría es obligatorio.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name + ' - ID : ' + str(self.pk)


class Feature(models.Model):
    name = models.CharField(max_length=200, validators=[MinLengthValidator(2)])
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def clean(self):
        # Prevent empty feature names from being persisted.
        super().clean()
        self.name = _normalize_name(self.name)
        if not self.name:
            raise ValidationError({'name': 'El nombre de la característica es obligatorio.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        category_name = self.category.name if self.category else 'Sin categoría'
        return self.name + ' - Category : ' + category_name


class Distributor(models.Model):
    name = models.CharField(max_length=200, validators=[MinLengthValidator(2)])

    def clean(self):
        # Reject blank distributor names before saving.
        super().clean()
        self.name = _normalize_name(self.name)
        if not self.name:
            raise ValidationError({'name': 'El nombre del distribuidor es obligatorio.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    name = models.CharField(max_length=200, validators=[MinLengthValidator(2)])

    def clean(self):
        # Reject blank manufacturer names before saving.
        super().clean()
        self.name = _normalize_name(self.name)
        if not self.name:
            raise ValidationError({'name': 'El nombre del fabricante es obligatorio.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=200, validators=[MinLengthValidator(2)])

    def clean(self):
        # Reject blank brand names before saving.
        super().clean()
        self.name = _normalize_name(self.name)
        if not self.name:
            raise ValidationError({'name': 'El nombre de la marca es obligatorio.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200, validators=[MinLengthValidator(2)])
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=3000, validators=[MinLengthValidator(10)])
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, null=True, blank=True)
    distributor = models.ForeignKey(Distributor, on_delete=models.CASCADE, null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    # Use DecimalField for money fields to support cents accurately and avoid float rounding issues.
    msrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    units = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    # Shipping dimensions — used to calculate shipping cost
    weight_kg = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal('1.000'), verbose_name='Peso (kg)')
    height_cm = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal('10.0'), verbose_name='Alto (cm)')
    width_cm = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal('10.0'), verbose_name='Ancho (cm)')
    length_cm = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal('10.0'), verbose_name='Largo (cm)')
    views_count = models.PositiveIntegerField(default=0, verbose_name='Conteo de visitas')



    def clean(self):
        # Validate product requirements before save to prevent incomplete records.
        super().clean()
        self.name = _normalize_name(self.name)
        self.description = _normalize_name(self.description)
        if not self.name:
            raise ValidationError({'name': 'El nombre del producto es obligatorio.'})
        if not self.description:
            raise ValidationError({'description': 'La descripción del producto es obligatoria.'})
        if self.category_id is None:
            raise ValidationError({'category': 'La categoría es obligatoria.'})
        if self.price is None or self.price < 1:
            raise ValidationError({'price': 'El precio debe ser mayor a 0.'})
        if self.units is None or self.units < 0:
            raise ValidationError({'units': 'Las unidades no pueden ser negativas.'})
        if self.msrp is not None and self.msrp < 1:
            raise ValidationError({'msrp': 'El MSRP debe ser mayor a 0 si se proporciona.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_all_images(self):
        """Devuelve una lista de dicts con url, is_main, id para la imagen principal y las secundarias."""
        all_imgs = []
        if self.image:
            all_imgs.append({'url': self.image.url, 'is_main': True, 'id': None})
        for img in self.images.all():
            all_imgs.append({'url': img.image.url, 'is_main': False, 'id': img.id})
        return all_imgs

    def get_average_rating(self):
        """Calcula el promedio de estrellas (1.0 a 5.0)."""
        avg = self.reviews.aggregate(models.Avg('rating'))['rating__avg']
        return round(float(avg), 1) if avg is not None else 0.0

    def get_review_count(self):
        """Devuelve el total de opiniones recibidas."""
        return self.reviews.count()

    def __str__(self):
        category_name = self.category.name if self.category else 'Sin categoría'
        return self.name + ' - Category : ' + category_name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/extra/', verbose_name='Imagen adicional')
    alt_text = models.CharField(max_length=200, blank=True, default='', verbose_name='Texto alternativo')
    order = models.PositiveIntegerField(default=0, verbose_name='Orden')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Imagen de Producto'
        verbose_name_plural = 'Imágenes de Productos'

    def __str__(self):
        return f"Imagen de {self.product.name} (#{self.id})"


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Calificación (1-5 estrellas)'
    )
    title = models.CharField(max_length=150, verbose_name='Título de la opinión')
    comment = models.TextField(verbose_name='Comentario u opinión')
    is_verified_purchase = models.BooleanField(default=False, verbose_name='Compra verificada')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')
        verbose_name = 'Reseña de Producto'
        verbose_name_plural = 'Reseñas de Productos'

    def __str__(self):
        return f"{self.rating}★ - {self.title} ({self.user.username})"



class FeatureValue(models.Model):
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    value = models.CharField(max_length=300, null=True, blank=True)

    def clean(self):
        # Avoid empty feature values when the form submits blanks.
        super().clean()
        self.value = _normalize_name(self.value)
        if not self.value:
            self.value = None

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        value_text = self.value or 'Sin valor'
        return value_text + ' - Feature : ' + self.feature.name + ' - Product : ' + self.product.name



class StoreSettings(models.Model):
    """Singleton model — only one record should exist. Stores global store configuration."""
    store_name = models.CharField(max_length=200, default='Store Django', verbose_name='Nombre de la tienda')
    store_email = models.EmailField(blank=True, default='', verbose_name='Email de la tienda')
    store_phone = models.CharField(max_length=30, blank=True, default='', verbose_name='Teléfono de la tienda')
    origin_commune = models.CharField(max_length=100, default='Pichidegua', verbose_name='Comuna de despacho')
    origin_address = models.CharField(max_length=250, blank=True, default='', verbose_name='Dirección de bodega')
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('59990.00'),
        verbose_name='Monto mínimo para envío gratis (CLP)',
    )
    # Shipit integration (future)
    shipit_email = models.EmailField(blank=True, default='', verbose_name='Email cuenta Shipit')
    shipit_token = models.CharField(max_length=200, blank=True, default='', verbose_name='Token API Shipit')
    shipit_enabled = models.BooleanField(default=False, verbose_name='Activar integración Shipit')

    # Personalización de Marca y Branding
    site_logo = models.ImageField(upload_to='store_branding/', null=True, blank=True, verbose_name='Logo de la tienda')
    site_favicon = models.ImageField(upload_to='store_branding/', null=True, blank=True, verbose_name='Favicon')
    footer_text = models.CharField(
        max_length=300,
        default='Plataforma de comercio electrónico con despacho y seguimiento en línea.',
        verbose_name='Texto de pie de página',
    )

    # Banners Promocionales del Carrusel
    banner1_title = models.CharField(max_length=150, default='Promoción del mes', verbose_name='Banner 1 Título')
    banner1_subtitle = models.CharField(max_length=300, default='Aprovecha descuentos especiales en productos seleccionados.', verbose_name='Banner 1 Subtítulo')
    banner1_bg_color = models.CharField(max_length=30, default='bg-primary text-white', verbose_name='Banner 1 Estilo/Color')

    banner2_title = models.CharField(max_length=150, default='Envío gratis', verbose_name='Banner 2 Título')
    banner2_subtitle = models.CharField(max_length=300, default='Disfruta de envío gratis en pedidos sobre el monto mínimo.', verbose_name='Banner 2 Subtítulo')
    banner2_bg_color = models.CharField(max_length=30, default='bg-success text-white', verbose_name='Banner 2 Estilo/Color')

    banner3_title = models.CharField(max_length=150, default='Nuevos lanzamientos', verbose_name='Banner 3 Título')
    banner3_subtitle = models.CharField(max_length=300, default='Descubre la colección más reciente para esta temporada.', verbose_name='Banner 3 Subtítulo')
    banner3_bg_color = models.CharField(max_length=30, default='bg-warning text-dark', verbose_name='Banner 3 Estilo/Color')

    enable_live_sales_notifications = models.BooleanField(default=True, verbose_name='Habilitar avisos de compras recientes en vivo')

    # Widget de WhatsApp Live Support
    whatsapp_number = models.CharField(max_length=30, default='+56912345678', verbose_name='Número de WhatsApp de atención (+569...)')
    whatsapp_default_message = models.CharField(max_length=250, default='Hola! Quisiera más información sobre la tienda.', verbose_name='Mensaje inicial de WhatsApp por defecto')
    enable_whatsapp_widget = models.BooleanField(default=True, verbose_name='Habilitar botón flotante de WhatsApp')




    class Meta:
        verbose_name = 'Configuración de la Tienda'

    def __str__(self):
        return f'Configuración: {self.store_name}'

    @classmethod
    def get_solo(cls):
        """Always returns the single settings record, creating it if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1  # Enforce singleton
        super().save(*args, **kwargs)


class ShippingRate(models.Model):
    """Internal shipping rate table — fallback when Shipit is not configured."""
    region = models.CharField(max_length=150, verbose_name='Región destino')
    weight_min_kg = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal('0.000'), verbose_name='Peso mínimo (kg)')
    weight_max_kg = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal('5.000'), verbose_name='Peso máximo (kg)')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio del envío (CLP)')
    courier_name = models.CharField(max_length=100, default='Starken', verbose_name='Courier')
    estimated_days = models.CharField(max_length=50, default='3-5 días hábiles', verbose_name='Días estimados')
    is_active = models.BooleanField(default=True, verbose_name='Activa')

    class Meta:
        verbose_name = 'Tarifa de Envío'
        verbose_name_plural = 'Tarifas de Envío'
        ordering = ['region', 'weight_min_kg']

    def __str__(self):
        return f'{self.region} | {self.weight_min_kg}–{self.weight_max_kg} kg → ${self.price:,.0f} ({self.courier_name})'


ORDER_STATUS_CHOICES = [
    ('pending', 'Pendiente de Pago'),
    ('paid', 'Pagada / En Preparación'),
    ('shipped', 'Enviada / En Camino'),
    ('completed', 'Entregada / Completada'),
    ('cancelled', 'Cancelada'),
]

PAYMENT_METHOD_CHOICES = [
    ('webpay', 'Webpay Plus (Transbank)'),
    ('mercadopago', 'Mercado Pago'),
    ('sandbox_card', 'Tarjeta de Crédito / Débito (Directa)'),
    ('transfer', 'Transferencia Bancaria Manual'),
]


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    first_name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])
    last_name = models.CharField(max_length=100, validators=[MinLengthValidator(2)])
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=250, validators=[MinLengthValidator(5)])
    city = models.CharField(max_length=100, validators=[MinLengthValidator(2)], verbose_name='Comuna / Ciudad')
    region = models.CharField(max_length=100, blank=True, default='', verbose_name='Región / Estado')
    country = models.CharField(max_length=100, blank=True, default='Chile', verbose_name='País')
    postal_code = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    paid = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='webpay', verbose_name='Método de pago')
    payment_transaction_id = models.CharField(max_length=150, blank=True, verbose_name='ID de transacción')
    payment_auth_code = models.CharField(max_length=50, blank=True, verbose_name='Código de autorización')
    payment_card_last4 = models.CharField(max_length=10, blank=True, verbose_name='Últimos 4 dígitos')
    payment_card_type = models.CharField(max_length=50, blank=True, verbose_name='Tipo de tarjeta')
    payment_installments = models.IntegerField(default=1, verbose_name='Número de cuotas')
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de confirmación de pago')
    tracking_company = models.CharField(max_length=100, blank=True, verbose_name='Empresa de transporte')
    tracking_number = models.CharField(max_length=100, blank=True, verbose_name='Número de seguimiento')
    notes = models.TextField(blank=True, verbose_name='Notas de despacho')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Latitud de entrega')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Longitud de entrega')
    # Shipping cost snapshot
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Costo de envío (CLP)')
    shipping_courier = models.CharField(max_length=100, blank=True, default='', verbose_name='Courier de envío')
    shipping_estimated_days = models.CharField(max_length=50, blank=True, default='', verbose_name='Días estimados de entrega')
    coupon = models.ForeignKey('Coupon', null=True, blank=True, on_delete=models.SET_NULL, related_name='orders', verbose_name='Cupón Aplicado')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Monto Descontado')



    def clean(self):
        super().clean()
        self.first_name = _normalize_name(self.first_name)
        self.last_name = _normalize_name(self.last_name)
        self.phone = _normalize_name(self.phone)
        self.address = _normalize_name(self.address)
        self.city = _normalize_name(self.city)
        self.region = _normalize_name(self.region)
        self.country = _normalize_name(self.country) or 'Chile'
        if not self.first_name:
            raise ValidationError({'first_name': 'El nombre es obligatorio.'})
        if not self.last_name:
            raise ValidationError({'last_name': 'El apellido es obligatorio.'})
        if self.phone:
            digits = re.sub(r'\D', '', self.phone)
            if len(digits) < 8:
                raise ValidationError({'phone': 'El teléfono debe contener al menos 8 dígitos.'})
        if not self.address:
            raise ValidationError({'address': 'La dirección es obligatoria.'})
        if not self.city:
            raise ValidationError({'city': 'La comuna o ciudad es obligatoria.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden #{self.pk} - {self.first_name} {self.last_name}"

    def get_full_address(self):
        parts = [self.address, self.city, self.region, self.country]
        return ', '.join([p for p in parts if p])

    def get_total_cost(self):

        return sum(item.get_cost() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    def __str__(self):
        product_name = self.product.name if self.product else 'Producto retirado'
        return f"{self.quantity}x {product_name} (Orden #{self.order_id})"

    def get_cost(self):
        return self.price * self.quantity


class ProductAuditLog(models.Model):
    ACTION_CHOICES = [
        ('soft_deleted', 'Archivado / Soft Delete'),
        ('restored', 'Restaurado'),
        ('hard_deleted', 'Eliminado Físicamente'),
    ]

    product_id = models.IntegerField()
    product_name = models.CharField(max_length=200)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default='soft_deleted')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_audit_logs',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    backup_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.get_action_display()} - {self.product_name} (ID: {self.product_id})"


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Porcentaje (%)'),
        ('fixed', 'Monto Fijo ($ CLP)'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='Código del Cupón')
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPE_CHOICES, default='percentage', verbose_name='Tipo de Descuento')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Valor del Descuento')
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Monto Mínimo de Compra')
    max_uses = models.PositiveIntegerField(null=True, blank=True, verbose_name='Límite de Usos Totales')
    used_count = models.PositiveIntegerField(default=0, verbose_name='Usos Realizados')
    valid_from = models.DateTimeField(default=timezone.now, verbose_name='Válido Desde')
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name='Válido Hasta')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cupón'
        verbose_name_plural = 'Cupones'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.discount_type == 'percentage':
            return f"{self.code} ({int(self.discount_value)}% OFF)"
        return f"{self.code} (${self.discount_value:,.0f} OFF)"

    def is_valid(self, order_total=Decimal('0.00')):
        now = timezone.now()
        if not self.is_active:
            return False, "El cupón no está activo."
        if self.valid_from and now < self.valid_from:
            return False, "El cupón aún no es válido."
        if self.valid_until and now > self.valid_until:
            return False, "El cupón ha expirado."
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, "El cupón ha alcanzado el límite máximo de usos."
        if order_total > 0 and order_total < self.min_purchase_amount:
            return False, f"El monto mínimo de compra para este cupón es $ {self.min_purchase_amount:,.0f} CLP."
        return True, "Cupón válido."

    def calculate_discount(self, order_total):
        valid, _ = self.is_valid(order_total)
        if not valid:
            return Decimal('0.00')
        if self.discount_type == 'percentage':
            discount = (order_total * self.discount_value) / Decimal('100.00')
        else:
            discount = self.discount_value
        return min(discount, order_total)


class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items', verbose_name='Usuario')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by', verbose_name='Producto')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de adición')

    class Meta:
        verbose_name = 'Ítem de Lista de Deseos'
        verbose_name_plural = 'Ítems de Lista de Deseos'
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.product.name}"