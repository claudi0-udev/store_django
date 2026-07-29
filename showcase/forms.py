from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'category',
            'brand',
            'manufacturer',
            'distributor',
            'description',
            'release_date',
            'msrp',
            'price',
            'units',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

        self.fields['name'].error_messages.update({
            'required': 'Please provide a product name',
            'min_length': 'Please provide a product name',
        })
        self.fields['category'].error_messages.update({
            'required': 'Please select a category',
        })
        self.fields['description'].error_messages.update({
            'required': 'Please provide a product description',
            'min_length': 'Please provide a product description',
        })
        self.fields['price'].error_messages.update({
            'required': 'Please provide a price',
            'min_value': 'Price must be at least 1',
            'invalid': 'Please enter a valid price',
        })

    def clean_name(self):
        name = self.cleaned_data.get('name', '')
        cleaned = name.strip()
        if not cleaned:
            raise forms.ValidationError('Please provide a product name')
        return cleaned

    def clean_description(self):
        description = self.cleaned_data.get('description', '')
        cleaned = description.strip()
        if not cleaned:
            raise forms.ValidationError('Please provide a product description')
        return cleaned

    def clean_category(self):
        category = self.cleaned_data.get('category')
        if category is None:
            raise forms.ValidationError('Please select a category')
        return category

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None:
            raise forms.ValidationError('Please provide a price')
        if price < 1:
            raise forms.ValidationError('Price must be at least 1')
        return price

    def clean_units(self):
        units = self.cleaned_data.get('units')
        if units is None:
            return 0
        if units < 0:
            raise forms.ValidationError('Units cannot be negative')
        return units
