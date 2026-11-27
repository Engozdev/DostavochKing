from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from orders.models import Order
from orders.services import _quote_data, _total, assignment_version, can_assign_courier, can_cancel_order
from tests.steps import step


class OrderRulesTests(SimpleTestCase):
    @step("Сумма заказа складывается из цен и количества")
    def test_total(self):
        items = [SimpleNamespace(line_total=Decimal("240.00")), SimpleNamespace(line_total=Decimal("50.50"))]
        self.assertEqual(_total(items), Decimal("290.50"))

    @step("Снимок корзины содержит версию и состав")
    def test_quote_data(self):
        cart = SimpleNamespace(user_id=3, pk=4, version=2)
        item = SimpleNamespace(product_id=8, quantity=2, product=SimpleNamespace(price=Decimal("120.00")))
        self.assertEqual(_quote_data(cart, [item]), {
            "client_id": 3, "cart_id": 4, "version": 2, "items": [[8, 2, "120.00"]]
        })

    @step("Назначение курьера доступно до принятия подтверждённого заказа")
    def test_assignment_rule(self):
        order = SimpleNamespace(status=Order.Status.CONFIRMED, accepted_at=None)
        self.assertTrue(can_assign_courier(order))
        order.accepted_at = object()
        self.assertFalse(can_assign_courier(order))

    @step("Отмена доступна только подтверждённому заказу")
    def test_cancellation_rule(self):
        self.assertTrue(can_cancel_order(SimpleNamespace(status=Order.Status.CONFIRMED)))
        self.assertFalse(can_cancel_order(SimpleNamespace(status=Order.Status.DELIVERED)))

    @step("Версия назначения меняется при смене курьера")
    def test_assignment_version(self):
        order = SimpleNamespace(pk="order-1", courier_id=1, assigned_at=None)
        before = assignment_version(order)
        order.courier_id = 2
        self.assertNotEqual(before, assignment_version(order))
