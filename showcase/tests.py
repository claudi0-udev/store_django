from decimal import Decimal
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from .models import Category, Order, OrderItem, Product, ProductAuditLog
from .views import AddNewProduct, HomePage, ListProducts, ProductDetail



class TestProductValidation(TestCase):
    def test_product_full_clean_rejects_blank_name_and_negative_price(self):
        product = Product(name='   ', description='Valid description', price=Decimal('0.00'), units=-1)

        with self.assertRaises(ValidationError):
            product.full_clean()


class TestHomePageView(TestCase):
    def test_home_page_renders_visitor_landing_content(self):
        request = RequestFactory().get('/')
        response = HomePage(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Descubre tu próxima compra')
        self.assertContains(response, 'Explorar catálogo')


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class TestAddProductView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User = get_user_model()
        self.staff_user = User.objects.create_user(username='staff_test', password='staffpass', is_staff=True)
        self.category = Category.objects.create(name='Tecnología')

    def test_add_new_product_rejects_missing_required_fields(self):
        request = self.factory.post(
            '/products/new',
            {
                'nameTxt': '',
                'categorySelect': '',
                'msrpTxt': '',
                'priceTxt': '0',
                'brandSelect': '',
                'manufacturerSelect': '',
                'distributorSelect': '',
                'unitsTxt': '0',
                'dateTxt': '',
                'descriptionTxtArea': '',
            },
        )
        request.user = self.staff_user

        initial_count = Product.objects.count()
        response = AddNewProduct(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Por favor ingresa un nombre para el producto')
        self.assertContains(response, 'Por favor selecciona una categoría')
        self.assertContains(response, 'El precio debe ser al menos 1')
        self.assertEqual(Product.objects.count(), initial_count)

    def test_add_new_product_success_with_image(self):
        # 1x1 transparent GIF image
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00'
            b'\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        )
        uploaded_image = SimpleUploadedFile('test_image.gif', small_gif, content_type='image/gif')

        request = self.factory.post(
            '/products/new',
            {
                'nameTxt': 'Producto con Imagen',
                'categorySelect': str(self.category.id),
                'msrpTxt': '150.00',
                'priceTxt': '120.00',
                'brandSelect': '',
                'manufacturerSelect': '',
                'distributorSelect': '',
                'unitsTxt': '10',
                'dateTxt': '2026-01-01',
                'descriptionTxtArea': 'Descripción detallada de prueba para el producto con imagen.',
                'image': uploaded_image,
            },
        )
        request.user = self.staff_user

        # Add session and messages support to request for redirect/messages
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))

        response = AddNewProduct(request)

        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(name='Producto con Imagen')
        self.assertTrue(bool(product.image))
        self.assertEqual(product.price, Decimal('120.00'))


class TestProductDetailAndList(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Ropa')
        self.product = Product.objects.create(
            name='Polera Básica',
            category=self.category,
            description='Polera 100% algodón orgánico suave.',
            price=Decimal('19.99'),
            units=15,
        )

    def test_products_list_view(self):
        request = RequestFactory().get('/products/')
        response = ListProducts(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Polera Básica')
        self.assertContains(response, 'Catálogo de Productos')

    def test_product_detail_view(self):
        request = RequestFactory().get(f'/products/detail/{self.product.id}')
        response = ProductDetail(request, productId=self.product.id)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Polera Básica')
        self.assertContains(response, 'Polera 100% algodón orgánico suave.')


class TestCart(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.category = Category.objects.create(name='Electrónica')
        self.p1 = Product.objects.create(
            name='Smartphone Alpha',
            category=self.category,
            description='Smartphone de alta gama con 128GB.',
            price=Decimal('500.00'),
            units=5,
        )
        self.p2 = Product.objects.create(
            name='Funda Protectora',
            category=self.category,
            description='Funda de silicona transparente.',
            price=Decimal('20.00'),
            units=10,
        )

    def _get_request_with_session(self, url='/'):
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware
        request = self.factory.get(url)
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))
        return request

    def test_cart_add_and_total_calculation(self):
        from .cart import Cart
        request = self._get_request_with_session()
        cart = Cart(request)

        cart.add(self.p1, quantity=2)
        cart.add(self.p2, quantity=1)

        self.assertEqual(len(cart), 3)
        self.assertEqual(cart.get_total_quantity(), 3)
        self.assertEqual(cart.get_total_price(), Decimal('1020.00'))

    def test_cart_decrement_and_remove(self):
        from .cart import Cart
        request = self._get_request_with_session()
        cart = Cart(request)

        cart.add(self.p1, quantity=2)
        cart.decrement(self.p1)
        self.assertEqual(len(cart), 1)

        cart.decrement(self.p1)
        self.assertEqual(len(cart), 0)

        cart.add(self.p2, quantity=3)
        cart.remove(self.p2)
        self.assertEqual(len(cart), 0)

    def test_cart_clear(self):
        from .cart import Cart
        request = self._get_request_with_session()
        cart = Cart(request)

        cart.add(self.p1, quantity=2)
        cart.add(self.p2, quantity=1)
        self.assertEqual(len(cart), 3)

        cart.clear()
        self.assertEqual(len(cart), 0)
        self.assertEqual(cart.get_total_price(), Decimal('0.00'))

    def test_cart_iterates_with_product_instance(self):
        from .cart import Cart
        request = self._get_request_with_session()
        cart = Cart(request)

        cart.add(self.p1, quantity=2)
        items = list(cart)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['product'].id, self.p1.id)
        self.assertEqual(items[0]['total_price'], Decimal('1000.00'))

    def test_cart_views_add_and_detail(self):
        # 1. Add to cart via view
        response = self.client.post(f'/cart/add/{self.p1.id}/', {'quantity': '2'})
        self.assertEqual(response.status_code, 302)

        # 2. View cart detail
        response_detail = self.client.get('/cart/')
        self.assertEqual(response_detail.status_code, 200)
        self.assertContains(response_detail, 'Smartphone Alpha')
        self.assertContains(response_detail, '1000')

        # 3. Update increment
        response_update = self.client.post(f'/cart/update/{self.p1.id}/', {'action': 'increment'})
        self.assertEqual(response_update.status_code, 302)

        # 4. Remove item
        response_remove = self.client.post(f'/cart/remove/{self.p1.id}/')
        self.assertEqual(response_remove.status_code, 302)

        # 5. Clear cart
        response_clear = self.client.post('/cart/clear/')
        self.assertEqual(response_clear.status_code, 302)


class TestOrdersAndCheckout(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='buyer', password='buyerpassword', email='buyer@example.com')
        self.category = Category.objects.create(name='Muebles')
        self.product = Product.objects.create(
            name='Silla Ergonómica',
            category=self.category,
            description='Silla de oficina con soporte lumbar ajustable.',
            price=Decimal('150.00'),
            units=10,
        )

    def test_checkout_redirects_if_cart_empty(self):
        response = self.client.get('/orders/checkout/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/products/')

    def test_checkout_creates_order_and_reduces_stock(self):
        from .models import Order, OrderItem

        # 1. Add product to cart
        self.client.post(f'/cart/add/{self.product.id}/', {'quantity': '2'})

        # 2. Submit checkout
        self.client.login(username='buyer', password='buyerpassword')
        response = self.client.post('/orders/checkout/', {
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan@example.com',
            'phone': '+56912345678',
            'address': 'Av. Libertador 1234',
            'city': 'Santiago',
            'postal_code': '8320000',
        })

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(email='juan@example.com')
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_amount, Decimal('300.00'))
        self.assertTrue(order.paid)
        self.assertEqual(order.status, 'paid')

        # Verify order items
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.price, Decimal('150.00'))

        # Verify stock decrement
        self.product.refresh_from_db()
        self.assertEqual(self.product.units, 8)

        # Verify cart is empty now
        cart_response = self.client.get('/cart/')
        self.assertContains(cart_response, 'Tu carrito está vacío')

    def test_order_history_requires_login(self):
        response = self.client.get('/orders/history/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_order_history_displays_user_orders(self):
        from .models import Order, OrderItem

        order = Order.objects.create(
            user=self.user,
            first_name='Juan',
            last_name='Pérez',
            email='buyer@example.com',
            phone='+56912345678',
            address='Calle 1',
            city='Valparaíso',
            total_amount=Decimal('150.00'),
            paid=True,
            status='paid',
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            price=Decimal('150.00'),
            quantity=1,
        )

        self.client.login(username='buyer', password='buyerpassword')
        response = self.client.get('/orders/history/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'#{order.id}')
        self.assertContains(response, 'Silla Ergonómica')

    def test_checkout_rejects_missing_or_invalid_phone(self):
        self.client.post(f'/cart/add/{self.product.id}/', {'quantity': '1'})

        # Missing phone
        response_missing = self.client.post('/orders/checkout/', {
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan@example.com',
            'phone': '',
            'address': 'Av. Libertador 1234',
            'city': 'Santiago',
        })
        self.assertEqual(response_missing.status_code, 200)
        self.assertContains(response_missing, 'Por favor ingresa tu número telefónico de contacto')

        # Short / invalid phone
        response_invalid = self.client.post('/orders/checkout/', {
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan@example.com',
            'phone': '123',
            'address': 'Av. Libertador 1234',
            'city': 'Santiago',
        })
        self.assertEqual(response_invalid.status_code, 200)
        self.assertContains(response_invalid, 'El número de teléfono debe contener al menos 8 dígitos válidos')

    def test_checkout_saves_delivery_coordinates_and_renders_on_map(self):
        self.client.post(f'/cart/add/{self.product.id}/', {'quantity': '1'})
        response = self.client.post('/orders/checkout/', {
            'first_name': 'Loreto',
            'last_name': 'Acuña',
            'email': 'loreto@example.com',
            'phone': '+56911223344',
            'address': 'Ahumada 48',
            'city': 'Santiago Centro',
            'postal_code': '8320000',
            'latitude': '-33.442900',
            'longitude': '-70.650400',
        })
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(email='loreto@example.com')
        self.assertEqual(order.latitude, Decimal('-33.442900'))
        self.assertEqual(order.longitude, Decimal('-70.650400'))




class TestProductAdminActions(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(username='staff_admin', password='password123', is_staff=True)
        self.customer_user = User.objects.create_user(username='regular_customer', password='password123', is_staff=False)
        self.category = Category.objects.create(name='Computación')
        self.product = Product.objects.create(
            name='Laptop Ultra 14',
            category=self.category,
            description='Laptop potente y ligera para trabajo intensivo.',
            price=Decimal('1200.00'),
            units=8,
        )

    def test_edit_product_requires_staff(self):
        # 1. Anonymous access
        response = self.client.get(f'/products/edit/{self.product.id}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

        # 2. Customer access
        self.client.login(username='regular_customer', password='password123')
        response = self.client.get(f'/products/edit/{self.product.id}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_edit_product_staff_success(self):
        self.client.login(username='staff_admin', password='password123')

        # GET form
        response = self.client.get(f'/products/edit/{self.product.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Laptop Ultra 14')

        # POST update
        response = self.client.post(f'/products/edit/{self.product.id}/', {
            'nameTxt': 'Laptop Ultra 14 Plus',
            'categorySelect': str(self.category.id),
            'msrpTxt': '1500.00',
            'priceTxt': '1100.00',
            'brandSelect': '',
            'manufacturerSelect': '',
            'distributorSelect': '',
            'unitsTxt': '12',
            'dateTxt': '2026-03-01',
            'descriptionTxtArea': 'Laptop actualizada con 32GB RAM y 1TB SSD.',
        })

        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Laptop Ultra 14 Plus')
        self.assertEqual(self.product.price, Decimal('1100.00'))
        self.assertEqual(self.product.units, 12)

    def test_delete_product_requires_staff(self):
        self.client.login(username='regular_customer', password='password123')
        response = self.client.post(f'/products/delete/{self.product.id}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertTrue(Product.objects.filter(id=self.product.id).exists())

    def test_delete_product_staff_success_performs_soft_delete_and_backup(self):
        from .models import ProductAuditLog

        self.client.login(username='staff_admin', password='password123')

        # GET confirm view
        response = self.client.get(f'/products/delete/{self.product.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '¿Estás seguro de que deseas retirar este producto del catálogo?')

        # POST soft delete
        response = self.client.post(f'/products/delete/{self.product.id}/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/products/')

        # Product still exists in DB but is inactive
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        self.assertIsNotNone(self.product.deleted_at)

        # Audit backup log created
        log = ProductAuditLog.objects.filter(product_id=self.product.id, action='soft_deleted').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.product_name, 'Laptop Ultra 14')
        self.assertEqual(log.backup_data['name'], 'Laptop Ultra 14')

    def test_soft_deleted_product_hidden_from_public_and_restorable(self):
        # 1. Archive the product
        self.product.is_active = False
        self.product.save()

        # 2. Public catalog hides it
        response_catalog = self.client.get('/products/')
        self.assertNotContains(response_catalog, 'Laptop Ultra 14')

        # 3. Public home hides it
        response_home = self.client.get('/')
        self.assertNotContains(response_home, 'Laptop Ultra 14')

        # 4. Public detail redirects
        response_detail = self.client.get(f'/products/detail/{self.product.id}/')
        self.assertEqual(response_detail.status_code, 302)

        # 5. Staff restores the product
        self.client.login(username='staff_admin', password='password123')
        response_restore = self.client.post(f'/products/restore/{self.product.id}/')
        self.assertEqual(response_restore.status_code, 302)

        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)
        self.assertIsNone(self.product.deleted_at)

        # 6. Public catalog shows it again
        self.client.logout()
        response_catalog_after = self.client.get('/products/')
        self.assertContains(response_catalog_after, 'Laptop Ultra 14')


class TestUserAuthenticationAndRegistration(TestCase):
    def setUp(self):
        User = get_user_model()
        self.existing_user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='password123',
            first_name='Carlos',
            last_name='Gómez',
        )

    def test_registration_view_renders_clean_form(self):
        response = self.client.get('/accounts/register/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Crea tu Cuenta de Cliente')
        self.assertContains(response, 'Correo electrónico')

    def test_registration_creates_customer_user_and_logs_in(self):
        User = get_user_model()
        response = self.client.post('/accounts/register/', {
            'first_name': 'Ana',
            'last_name': 'Silva',
            'username': 'anasilva',
            'email': 'ana.silva@example.com',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
        })
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username='anasilva')
        self.assertEqual(user.first_name, 'Ana')
        self.assertEqual(user.last_name, 'Silva')
        self.assertEqual(user.email, 'ana.silva@example.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        # Check session is logged in
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post('/accounts/register/', {
            'first_name': 'Pedro',
            'last_name': 'Rojas',
            'username': 'pedrorojas',
            'email': 'pedro@example.com',
            'password': 'password123',
            'password_confirm': 'differentpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Las contraseñas no coinciden')

    def test_registration_rejects_duplicate_email(self):
        response = self.client.post('/accounts/register/', {
            'first_name': 'Otro',
            'last_name': 'Usuario',
            'username': 'uniqueusername',
            'email': 'existing@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una cuenta registrada con este correo electrónico')

    def test_login_view_valid_credentials(self):
        response = self.client.post('/accounts/login/', {
            'username': 'existinguser',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.existing_user.id)

    def test_login_view_invalid_credentials_shows_clear_error(self):
        response = self.client.post('/accounts/login/', {
            'username': 'existinguser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nombre de usuario o contraseña incorrectos')

    def test_authenticated_user_redirected_away_from_login_and_register(self):
        self.client.login(username='existinguser', password='password123')

        response_login = self.client.get('/accounts/login/')
        self.assertEqual(response_login.status_code, 302)

        response_register = self.client.get('/accounts/register/')
        self.assertEqual(response_register.status_code, 302)


class TestOrderConfirmationEmail(TestCase):
    def setUp(self):
        from django.core import mail
        mail.outbox = []
        self.category = Category.objects.create(name='Computación')
        self.product = Product.objects.create(
            name='Monitor 27 4K',
            description='Monitor profesional con resolución 4K HDR.',
            price=Decimal('450.00'),
            units=10,
            category=self.category,
        )


    def test_order_checkout_sends_confirmation_email(self):
        from django.core import mail

        # 1. Add product to cart
        self.client.post(f'/cart/add/{self.product.id}/', {'quantity': 2})

        # 2. Checkout
        response = self.client.post('/orders/checkout/', {
            'first_name': 'Camila',
            'last_name': 'Valenzuela',
            'email': 'camila.valenzuela@example.cl',
            'phone': '+56912345678',
            'address': 'Av. Providencia 1234',
            'city': 'Santiago',
            'postal_code': '7500000',
        })
        self.assertEqual(response.status_code, 302)

        # 3. Verify email sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('camila.valenzuela@example.cl', email.to)
        self.assertIn('Confirmación de Pedido', email.subject)
        self.assertIn('Monitor 27 4K', email.body)
        self.assertIn('900', email.body)


class TestStaffOrderManagement(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            username='staff_manager',
            password='password123',
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username='customer_user',
            password='password123',
            is_staff=False,
        )
        self.category = Category.objects.create(name='Audio')
        self.product = Product.objects.create(
            name='Audífonos Noise Cancelling',
            description='Cancelación de ruido activa de alta fidelidad.',
            price=Decimal('200.00'),
            units=15,
            category=self.category,
        )
        self.order1 = Order.objects.create(
            user=self.regular_user,
            first_name='Martín',
            last_name='Soto',
            email='martin.soto@example.com',
            phone='+56999887766',
            address='Av. Las Condes 500',
            city='Santiago',
            status='paid',
            paid=True,
            total_amount=Decimal('400.00'),
        )
        OrderItem.objects.create(
            order=self.order1,
            product=self.product,
            price=Decimal('200.00'),
            quantity=2,
        )

    def test_manage_orders_requires_staff(self):
        # 1. Anonymous user
        response = self.client.get('/manage/orders/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

        # 2. Regular customer user
        self.client.login(username='customer_user', password='password123')
        response_customer = self.client.get('/manage/orders/')
        self.assertEqual(response_customer.status_code, 302)
        self.assertIn('/accounts/login/', response_customer.url)

    def test_manage_orders_renders_for_staff(self):
        self.client.login(username='staff_manager', password='password123')
        response = self.client.get('/manage/orders/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Panel de Gestión y Despacho de Pedidos')
        self.assertContains(response, 'Martín Soto')
        self.assertContains(response, '+56999887766')

    def test_manage_orders_filter_and_search(self):
        self.client.login(username='staff_manager', password='password123')

        # Filter by paid
        response_paid = self.client.get('/manage/orders/?status=paid')
        self.assertEqual(response_paid.status_code, 200)
        self.assertContains(response_paid, 'Martín Soto')

        # Filter by pending (should be empty)
        response_pending = self.client.get('/manage/orders/?status=pending')
        self.assertEqual(response_pending.status_code, 200)
        self.assertNotContains(response_pending, 'Martín Soto')

        # Search by phone
        response_search = self.client.get('/manage/orders/?q=99887766')
        self.assertEqual(response_search.status_code, 200)
        self.assertContains(response_search, 'Martín Soto')

    def test_manage_order_detail_view(self):
        self.client.login(username='staff_manager', password='password123')
        response = self.client.get(f'/manage/orders/{self.order1.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Gestión de Pedido #{self.order1.id}')
        self.assertContains(response, 'Audífonos Noise Cancelling')

    def test_manage_order_update_status_and_tracking(self):
        self.client.login(username='staff_manager', password='password123')
        response = self.client.post(f'/manage/orders/{self.order1.id}/update/', {
            'status': 'shipped',
            'paid': 'true',
            'tracking_company': 'Chilexpress',
            'tracking_number': 'CHI-9988771122',
            'notes': 'Entregar en conserjería del edificio.',
        })
        self.assertEqual(response.status_code, 302)

        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'shipped')
        self.assertEqual(self.order1.tracking_company, 'Chilexpress')
        self.assertEqual(self.order1.tracking_number, 'CHI-9988771122')
        self.assertEqual(self.order1.notes, 'Entregar en conserjería del edificio.')

    def test_legacy_order_without_phone_can_be_updated_safely(self):
        # Create a legacy order with no phone
        legacy_order = Order.objects.create(
            user=self.regular_user,
            first_name='Antiguo',
            last_name='Cliente',
            email='legacy@example.com',
            phone='',
            address='Calle Antigua 123',
            city='Santiago',
            status='pending',
            paid=False,
            total_amount=Decimal('200.00'),
        )

        self.client.login(username='staff_manager', password='password123')

        # 1. Staff can update status even if phone is still blank
        response = self.client.post(f'/manage/orders/{legacy_order.id}/update/', {
            'status': 'paid',
            'paid': 'true',
            'phone': '',
            'tracking_company': '',
            'tracking_number': '',
            'notes': 'Pago verificado por transferencia.',
        })
        self.assertEqual(response.status_code, 302)

        legacy_order.refresh_from_db()
        self.assertEqual(legacy_order.status, 'paid')
        self.assertTrue(legacy_order.paid)

        # 2. Staff can also add a phone number to it
        response2 = self.client.post(f'/manage/orders/{legacy_order.id}/update/', {
            'status': 'shipped',
            'paid': 'true',
            'phone': '+56987654321',
            'tracking_company': 'Starken',
            'tracking_number': 'STK-112233',
        })
        self.assertEqual(response2.status_code, 302)

        legacy_order.refresh_from_db()
        self.assertEqual(legacy_order.status, 'shipped')
        self.assertEqual(legacy_order.phone, '+56987654321')











