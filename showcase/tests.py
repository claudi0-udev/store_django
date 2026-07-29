from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase

from .models import Product
from .views import AddNewProduct


class ProductValidationTests(TestCase):
    def test_product_full_clean_rejects_blank_name_and_negative_price(self):
        product = Product(name='   ', description='Valid description', price=0, units=-1)

        with self.assertRaises(ValidationError):
            product.full_clean()


class AddProductViewTests(TestCase):
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

        response = AddNewProduct(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.count(), 0)
