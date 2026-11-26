import uuid

from django.db import models


class PaymentAttempt(models.Model):
    class Result(models.TextChoices):
        PENDING = "PENDING", "Ожидает оплаты"
        SUCCEEDED = "SUCCEEDED", "Успешно"
        FAILED = "FAILED", "Ошибка"

    class FailureReason(models.TextChoices):
        MOCK_DECLINED = "MOCK_DECLINED", "Учебный платёж отклонён. Попробуйте снова."
        YOOKASSA_DECLINED = "YOOKASSA_DECLINED", "ЮKassa отклонила платёж. Попробуйте снова."
        PRODUCT_UNAVAILABLE = "PRODUCT_UNAVAILABLE", "Некоторых товаров больше нет в нужном количестве."

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payment_attempts")
    attempt_key = models.UUIDField()
    provider = models.CharField(max_length=16, default="mock")
    result = models.CharField(max_length=9, choices=Result)
    failure_reason = models.CharField(max_length=32, choices=FailureReason, blank=True)
    amount = models.DecimalField(max_digits=28, decimal_places=2)
    currency = models.CharField(max_length=3)
    provider_payment_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    confirmation_url = models.URLField(max_length=2048, blank=True)
    return_url = models.URLField(max_length=2048, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(fields=("order", "attempt_key"), name="payment_attempt_key_unique"),
            models.UniqueConstraint(
                fields=("order",), condition=models.Q(result="SUCCEEDED"), name="payment_one_success_per_order"
            ),
            models.UniqueConstraint(
                fields=("order",), condition=models.Q(result="PENDING"), name="payment_one_pending_per_order"
            ),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="payment_amount_nonnegative"),
        ]


class PaymentRefund(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Ожидает подтверждения"
        SUCCEEDED = "SUCCEEDED", "Выполнен"
        CANCELED = "CANCELED", "Отклонён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_attempt = models.ForeignKey(PaymentAttempt, on_delete=models.PROTECT, related_name="refunds")
    status = models.CharField(max_length=9, choices=Status, default=Status.PENDING)
    amount = models.DecimalField(max_digits=28, decimal_places=2)
    currency = models.CharField(max_length=3)
    provider_refund_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("payment_attempt",),
                condition=models.Q(status="PENDING"),
                name="payment_refund_one_pending",
            ),
            models.UniqueConstraint(
                fields=("payment_attempt",),
                condition=models.Q(status="SUCCEEDED"),
                name="payment_refund_one_success",
            ),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_refund_amount_positive"),
        ]
