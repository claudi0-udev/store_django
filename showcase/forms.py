from django import forms

from .models import Order, Product



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
            'image',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'image':
                field.widget.attrs.setdefault('class', 'form-control-file')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

        self.fields['name'].error_messages.update({
            'required': 'Por favor ingresa un nombre para el producto',
            'min_length': 'Por favor ingresa un nombre para el producto',
        })
        self.fields['category'].error_messages.update({
            'required': 'Por favor selecciona una categoría',
        })
        self.fields['description'].error_messages.update({
            'required': 'Por favor ingresa una descripción',
            'min_length': 'Por favor ingresa una descripción',
        })
        self.fields['price'].error_messages.update({
            'required': 'Por favor ingresa un precio',
            'min_value': 'El precio debe ser al menos 1',
            'invalid': 'Por favor ingresa un precio válido',
        })

    def clean_name(self):
        name = self.cleaned_data.get('name', '')
        cleaned = name.strip()
        if not cleaned:
            raise forms.ValidationError('Por favor ingresa un nombre para el producto')
        return cleaned

    def clean_description(self):
        description = self.cleaned_data.get('description', '')
        cleaned = description.strip()
        if not cleaned:
            raise forms.ValidationError('Por favor ingresa una descripción')
        return cleaned

    def clean_category(self):
        category = self.cleaned_data.get('category')
        if category is None:
            raise forms.ValidationError('Por favor selecciona una categoría')
        return category

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None:
            raise forms.ValidationError('Por favor ingresa un precio')
        if price < 1:
            raise forms.ValidationError('El precio debe ser al menos 1')
        return price

    def clean_units(self):
        units = self.cleaned_data.get('units')
        if units is None:
            return 0
        if units < 0:
            raise forms.ValidationError('Las unidades no pueden ser negativas')
        return units


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'city',
            'region',
            'country',
            'postal_code',
            'latitude',
            'longitude',
        ]
        widgets = {
            'latitude': forms.HiddenInput(attrs={'id': 'id_latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'id_longitude'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.setdefault('class', 'form-control')

        self.fields['first_name'].error_messages.update({
            'required': 'Por favor ingresa tu nombre',
        })
        self.fields['last_name'].error_messages.update({
            'required': 'Por favor ingresa tu apellido',
        })
        self.fields['email'].error_messages.update({
            'required': 'Por favor ingresa tu correo electrónico',
            'invalid': 'Por favor ingresa un correo electrónico válido',
        })
        self.fields['address'].error_messages.update({
            'required': 'Por favor ingresa tu dirección de entrega',
        })
        self.fields['city'].error_messages.update({
            'required': 'Por favor ingresa tu comuna o ciudad',
        })
        self.fields['city'].widget.attrs.update({
            'placeholder': 'Ej: Santiago, Providencia, Las Condes...',
        })
        self.fields['region'].widget.attrs.update({
            'placeholder': 'Ej: Región Metropolitana de Santiago',
        })
        self.fields['country'].widget.attrs.update({
            'placeholder': 'Ej: Chile',
        })
        self.fields['phone'].required = True
        self.fields['phone'].widget.attrs.update({
            'placeholder': 'Ej: +56 9 1234 5678',
        })
        self.fields['phone'].error_messages.update({
            'required': 'Por favor ingresa tu número telefónico de contacto',
        })


    def clean_phone(self):
        import re
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone:
            raise forms.ValidationError('Por favor ingresa tu número telefónico de contacto')
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 8:
            raise forms.ValidationError('El número de teléfono debe contener al menos 8 dígitos válidos')
        return phone



from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo 6 caracteres'}),
        min_length=6,
        error_messages={
            'required': 'Por favor ingresa una contraseña',
            'min_length': 'La contraseña debe tener al menos 6 caracteres',
        },
    )
    password_confirm = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repite tu contraseña'}),
        error_messages={
            'required': 'Por favor confirma tu contraseña',
        },
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
        }
        help_texts = {
            'username': '',
        }
        error_messages = {
            'username': {
                'required': 'Por favor ingresa un nombre de usuario',
                'unique': 'Este nombre de usuario ya está en uso',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.PasswordInput):
                field.widget.attrs.setdefault('class', 'form-control')

        self.fields['first_name'].widget.attrs.setdefault('placeholder', 'Ej: Juan')
        self.fields['last_name'].widget.attrs.setdefault('placeholder', 'Ej: Pérez')
        self.fields['username'].widget.attrs.setdefault('placeholder', 'Ej: juanperez')
        self.fields['email'].widget.attrs.setdefault('placeholder', 'ejemplo@correo.com')
        self.fields['email'].required = True

        self.fields['first_name'].error_messages.update({'required': 'Por favor ingresa tu nombre'})
        self.fields['last_name'].error_messages.update({'required': 'Por favor ingresa tu apellido'})
        self.fields['email'].error_messages.update({
            'required': 'Por favor ingresa tu correo electrónico',
            'invalid': 'Por favor ingresa un correo electrónico válido',
        })

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError('El correo electrónico es obligatorio')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta registrada con este correo electrónico')
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Las contraseñas no coinciden')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': 'Tu nombre de usuario',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control form-control-lg',
            'placeholder': '••••••••',
        })
        self.error_messages.update({
            'invalid_login': 'Nombre de usuario o contraseña incorrectos. Por favor verifica tus datos.',
            'inactive': 'Esta cuenta se encuentra inactiva.',
        })



