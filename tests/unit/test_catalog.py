from django.test import SimpleTestCase

from catalog.models import Product
from tests.steps import step


class ProductRulesTests(SimpleTestCase):
    @step("Активный товар с остатком доступен для покупки")
    def test_available_product(self):
        self.assertTrue(Product(is_active=True, stock_quantity=1).is_available)

    @step("Скрытый товар не доступен даже при наличии остатка")
    def test_hidden_product(self):
        self.assertFalse(Product(is_active=False, stock_quantity=10).is_available)
