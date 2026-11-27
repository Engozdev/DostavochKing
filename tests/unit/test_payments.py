from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from payments.gateway import MockPaymentGateway
from payments.models import PaymentAttempt
from payments.services import _validate_payment, _payment_url, can_repeat_creation
from payments.yookassa import YooKassaError
from tests.steps import step


class PaymentRulesTests(SimpleTestCase):
    @step("Учебный шлюз принимает успешную оплату в рублях")
    def test_mock_gateway_accepts_success(self):
        result = MockPaymentGateway.charge(
            amount=Decimal("120.00"), currency="RUB", outcome=PaymentAttempt.Result.SUCCEEDED
        )
        self.assertEqual(result, PaymentAttempt.Result.SUCCEEDED)

    @step("Учебный шлюз отклоняет некорректную валюту")
    def test_mock_gateway_rejects_currency(self):
        with self.assertRaises(ValueError):
            MockPaymentGateway.charge(
                amount=Decimal("120.00"), currency="USD", outcome=PaymentAttempt.Result.SUCCEEDED
            )

    @step("Ответ внешнего шлюза сверяется с суммой заказа")
    def test_provider_payment_rejects_wrong_amount(self):
        attempt = SimpleNamespace(amount=Decimal("120.00"), currency="RUB", provider_payment_id=None)
        response = {"id": "pay-1", "status": "succeeded", "paid": True, "test": True,
                    "amount": {"value": "119.00", "currency": "RUB"}}
        with self.assertRaises(YooKassaError):
            _validate_payment(attempt, response)

    @step("Для оплаты принимается только HTTPS-ссылка")
    def test_confirmation_url_rejects_http(self):
        with self.assertRaises(YooKassaError):
            _payment_url({"confirmation": {"confirmation_url": "http://example.test/pay"}})

    @step("Повторное создание платежа ограничено 24 часами")
    def test_creation_window_expires(self):
        from datetime import datetime, timedelta, timezone

        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        with patch("payments.services.timezone.now", return_value=now):
            self.assertTrue(can_repeat_creation(SimpleNamespace(created_at=now - timedelta(hours=23))))
            self.assertFalse(can_repeat_creation(SimpleNamespace(created_at=now - timedelta(hours=24))))
