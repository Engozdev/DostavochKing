from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from cart.services import CartError, CartVersionConflict, _require_available_quantity, _require_version
from tests.steps import step


class CartRulesTests(SimpleTestCase):
    @step("Устаревшая версия корзины вызывает конфликт")
    def test_stale_version(self):
        with self.assertRaises(CartVersionConflict):
            _require_version(SimpleNamespace(version=2), 1)

    @step("Количество выше остатка отклоняется")
    def test_quantity_exceeds_stock(self):
        item = SimpleNamespace(is_available=True, stock_quantity=2, name="Молоко")
        with self.assertRaises(CartError):
            _require_available_quantity(item, 3)

    @step("Товар без остатка недоступен для добавления")
    def test_unavailable_product(self):
        item = SimpleNamespace(is_available=False, stock_quantity=0, name="Молоко")
        with self.assertRaises(CartError):
            _require_available_quantity(item, 1)
