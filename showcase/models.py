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
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True)
    description = models.CharField(max_length=3000, validators=[MinLengthValidator(10)])
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, null=True)
    distributor = models.ForeignKey(Distributor, on_delete=models.CASCADE, null=True)
    release_date = models.DateField(null=True, blank=True)
    # Use DecimalField for money fields to support cents accurately and avoid float rounding issues.
    msrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    units = models.IntegerField(default=0, validators=[MinValueValidator(0)])

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