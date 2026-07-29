from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from .models import Product
from .views import AddNewProduct


class TestProductValidation(TestCase):
    def test_product_full_clean_rejects_blank_name_and_negative_price(self):
        product = Product(name='   ', description='Valid description', price=Decimal('0.00'), units=-1)

        with self.assertRaises(ValidationError):
            product.full_clean()


class TestAddProductView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

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

        initial_count = Product.objects.count()
        response = AddNewProduct(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please provide a product name')
        self.assertContains(response, 'Please select a category')
        self.assertContains(response, 'Price must be at least 1')
        self.assertEqual(Product.objects.count(), initial_count)

    def test_add_new_product_returns_validation_errors_in_response(self):
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

        initial_count = Product.objects.count()
        response = AddNewProduct(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please provide a product name')
        self.assertContains(response, 'Please select a category')
        self.assertContains(response, 'Price must be at least 1')
        self.assertEqual(Product.objects.count(), initial_count)
