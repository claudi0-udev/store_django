from decimal import Decimal
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, MinValueValidator
from django.db import models




def _normalize_name(value):
    return (value or '').strip()


class Category(models.Model):
    name = models.CharField(max_length=200, validators=[MinLengthValidator(2)])
    parent_category_id = models.IntegerField(null=True, blank=True)

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

    def __str__(self):
        category_name = self.category.name if self.category else 'Sin categoría'
        return self.name + ' - Category : ' + category_name


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


ORDER_STATUS_CHOICES = [
    ('pending', 'Pendiente'),
    ('paid', 'Pagada'),
    ('shipped', 'Enviada'),
    ('completed', 'Completada'),
    ('cancelled', 'Cancelada'),
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
    tracking_company = models.CharField(max_length=100, blank=True, verbose_name='Empresa de transporte')
    tracking_number = models.CharField(max_length=100, blank=True, verbose_name='Número de seguimiento')
    notes = models.TextField(blank=True, verbose_name='Notas de despacho')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Latitud de entrega')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Longitud de entrega')

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