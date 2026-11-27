from django.test import TestCase
from django.urls import reverse

from orders.models import Order
from payments.models import PaymentAttempt
from tests.factories import product, user
from tests.steps import step


class ClientJourneyTests(TestCase):
    def setUp(self):
        self.client_user = user()
        self.product = product()
        self.client.force_login(self.client_user)

    @step("Клиент проходит каталог, корзину, оформление и учебную оплату через HTTP")
    def test_purchase_journey(self):
        self.assertEqual(self.client.get(reverse("catalog:list")).status_code, 200)
        self.assertEqual(self.client.post(reverse("cart:add", args=[self.product.pk]), {"quantity": 2}).status_code, 302)
        checkout = self.client.get(reverse("orders:checkout"))
        self.assertEqual(checkout.status_code, 200)
        form = checkout.context["form"]
        response = self.client.post(reverse("orders:checkout"), {
            "delivery_address": "Москва, Тестовая 1",
            "checkout_key": str(form.initial["checkout_key"]),
            "quote": form.initial["quote"],
        })
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(client=self.client_user)
        payment = self.client.get(reverse("orders:mock_payment", args=[order.pk]))
        self.assertEqual(payment.status_code, 200)
        response = self.client.post(reverse("orders:mock_payment", args=[order.pk]), {
            "attempt_key": str(payment.context["form"].initial["attempt_key"]),
            "outcome": PaymentAttempt.Result.SUCCEEDED,
        })
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(self.client.get(reverse("orders:detail", args=[order.pk])).status_code, 200)

    @step("Гость направляется на вход при открытии корзины")
    def test_guest_cart_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
