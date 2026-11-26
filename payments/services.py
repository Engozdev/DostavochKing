from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from orders.models import Order
from orders.services import confirm_paid_order, get_client_order, list_client_orders

from .models import PaymentAttempt
from .yookassa import YooKassaError, YooKassaGateway


def can_repeat_creation(attempt):
    return timezone.now() < attempt.created_at + timedelta(hours=24)


@transaction.atomic
def _get_or_create_attempt(client, order_id):
    order = get_object_or_404(list_client_orders(client).select_for_update(), pk=order_id)
    if order.status != Order.Status.CREATED or order.payment_attempts.filter(
        result=PaymentAttempt.Result.SUCCEEDED
    ).exists():
        return None

    pending = order.payment_attempts.filter(provider="yookassa", result=PaymentAttempt.Result.PENDING).first()
    if pending:
        return pending

    if order.currency != "RUB" or not Decimal("1.00") <= order.total_amount <= Decimal("350000.00"):
        raise YooKassaError("Оплата картой доступна для заказов от 1 до 350 000 ₽.")

    attempt_key = uuid4()
    return_path = reverse("orders:payment_return", kwargs={"order_id": order.pk, "attempt_key": attempt_key})
    return order.payment_attempts.create(
        attempt_key=attempt_key,
        provider="yookassa",
        result=PaymentAttempt.Result.PENDING,
        amount=order.total_amount,
        currency=order.currency,
        return_url=f"{settings.YOOKASSA_RETURN_BASE_URL}{return_path}",
    )


def start_yookassa_payment(client, order_id):
    attempt = _get_or_create_attempt(client, order_id)
    if attempt is None or attempt.provider_payment_id:
        return attempt

    if not can_repeat_creation(attempt):
        raise YooKassaError("Не удалось подтвердить создание платежа. Обратитесь к администратору.")

    YooKassaGateway.ensure_test_shop()
    if not can_repeat_creation(attempt):
        raise YooKassaError("Не удалось подтвердить создание платежа. Обратитесь к администратору.")

    payment = YooKassaGateway.create_payment(
        amount=attempt.amount,
        currency=attempt.currency,
        attempt_key=attempt.attempt_key,
        return_url=attempt.return_url,
    )
    return _record_payment(client, order_id, attempt.attempt_key, payment)


def check_yookassa_payment(client, order_id, attempt_key):
    order = get_client_order(client, order_id)
    attempt = get_object_or_404(order.payment_attempts, provider="yookassa", attempt_key=attempt_key)
    if attempt.result == PaymentAttempt.Result.PENDING and attempt.provider_payment_id:
        payment = YooKassaGateway.get_payment(attempt.provider_payment_id)
        return _record_payment(client, order_id, attempt_key, payment)
    return attempt


def _validate_payment(attempt, payment):
    payment_id = payment.get("id")
    status = payment.get("status")
    try:
        amount = payment["amount"]["value"]
        amount_matches = isinstance(amount, str) and Decimal(amount) == attempt.amount
        currency_matches = payment["amount"]["currency"] == attempt.currency
    except (InvalidOperation, KeyError, TypeError, ValueError):
        amount_matches = currency_matches = False

    if (
        payment.get("test") is not True
        or not isinstance(payment_id, str)
        or not payment_id
        or len(payment_id) > 128
        or (attempt.provider_payment_id and payment_id != attempt.provider_payment_id)
        or not amount_matches
        or not currency_matches
        or status not in ("pending", "succeeded", "canceled")
        or (status == "succeeded" and payment.get("paid") is not True)
    ):
        raise YooKassaError("Не удалось сверить данные платежа с ЮKassa.")


def _payment_url(payment):
    try:
        url = payment["confirmation"]["confirmation_url"]
        if isinstance(url, str) and len(url) <= 2048:
            parsed = urlsplit(url)
            if parsed.scheme == "https" and parsed.hostname:
                return url
    except (KeyError, TypeError, ValueError):
        pass
    raise YooKassaError("ЮKassa не вернула ссылку для оплаты.")


@transaction.atomic
def _record_payment(client, order_id, attempt_key, payment):
    order = get_object_or_404(list_client_orders(client).select_for_update(), pk=order_id)
    attempt = get_object_or_404(order.payment_attempts, provider="yookassa", attempt_key=attempt_key)
    if attempt.result != PaymentAttempt.Result.PENDING:
        return attempt

    _validate_payment(attempt, payment)
    attempt.provider_payment_id = payment["id"]
    if payment["status"] == "pending" and not attempt.confirmation_url:
        attempt.confirmation_url = _payment_url(payment)
    elif payment["status"] == "canceled":
        attempt.result = PaymentAttempt.Result.FAILED
        attempt.failure_reason = PaymentAttempt.FailureReason.YOOKASSA_DECLINED
    elif payment["status"] == "succeeded":
        attempt.result = PaymentAttempt.Result.SUCCEEDED
        if not confirm_paid_order(order):
            attempt.failure_reason = PaymentAttempt.FailureReason.PRODUCT_UNAVAILABLE

    attempt.save(update_fields=["provider_payment_id", "confirmation_url", "result", "failure_reason"])
    return attempt
