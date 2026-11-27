from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from cart.models import Cart, CartItem
from cart.services import CartVersionConflict, add_item, update_item
from orders.models import Order, OrderItem
from orders.services import CheckoutConflict, confirm_mock_payment, create_order, get_checkout
from payments.models import PaymentAttempt
from tests.factories import product, user
from tests.steps import step


class CartOrderIntegrationTests(TestCase):
    def setUp(self):
        self.client_user = user()
        self.product = product()

    @step("Добавление товара создаёт строку корзины и повышает её версию")
    def test_add_item(self):
        add_item(self.client_user, self.product.pk, 2)
        cart = Cart.objects.get(user=self.client_user)
        self.assertEqual(cart.version, 1)
        self.assertEqual(CartItem.objects.get(cart=cart).quantity, 2)

    @step("Старая версия не меняет количество товара")
    def test_update_rejects_stale_version(self):
        add_item(self.client_user, self.product.pk, 2)
        with self.assertRaises(CartVersionConflict):
            update_item(self.client_user, self.product.pk, 3, version=0)
        self.assertEqual(CartItem.objects.get(cart=self.client_user.cart).quantity, 2)

    @step("Оформление сохраняет снимок заказа и очищает корзину")
    def test_checkout_creates_snapshot(self):
        add_item(self.client_user, self.product.pk, 2)
        _, total, quote = get_checkout(self.client_user)
        order = create_order(self.client_user, delivery_address="Москва, Тестовая 1", checkout_key=uuid4(), quote=quote)
        self.assertEqual(total, Decimal("240.00"))
        self.assertEqual(order.total_amount, total)
        self.assertEqual(OrderItem.objects.get(order=order).quantity, 2)
        self.assertFalse(CartItem.objects.filter(cart=self.client_user.cart).exists())

    @step("Повтор запроса с тем же ключом возвращает прежний заказ")
    def test_checkout_is_idempotent(self):
        add_item(self.client_user, self.product.pk, 1)
        _, _, quote = get_checkout(self.client_user)
        key = uuid4()
        first = create_order(self.client_user, delivery_address="Москва, Тестовая 1", checkout_key=key, quote=quote)
        second = create_order(self.client_user, delivery_address="Москва, Тестовая 1", checkout_key=key, quote=quote)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Order.objects.count(), 1)

    @step("Изменение корзины после получения предложения блокирует оформление")
    def test_checkout_rejects_stale_quote(self):
        add_item(self.client_user, self.product.pk, 1)
        _, _, quote = get_checkout(self.client_user)
        add_item(self.client_user, self.product.pk, 1)
        with self.assertRaises(CheckoutConflict):
            create_order(self.client_user, delivery_address="Москва, Тестовая 1", checkout_key=uuid4(), quote=quote)
        self.assertFalse(Order.objects.exists())

    @step("Успешная оплата подтверждает заказ и уменьшает остаток один раз")
    def test_payment_confirms_order_once(self):
        add_item(self.client_user, self.product.pk, 2)
        _, _, quote = get_checkout(self.client_user)
        order = create_order(self.client_user, delivery_address="Москва, Тестовая 1", checkout_key=uuid4(), quote=quote)
        key = uuid4()
        first = confirm_mock_payment(self.client_user, order_id=order.pk, attempt_key=key,
                                     outcome=PaymentAttempt.Result.SUCCEEDED)
        second = confirm_mock_payment(self.client_user, order_id=order.pk, attempt_key=key,
                                      outcome=PaymentAttempt.Result.SUCCEEDED)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(self.product.stock_quantity, 8)
