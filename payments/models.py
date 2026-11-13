import uuid

from django.db import models


class PaymentAttempt(models.Model):
    class Result(models.TextChoices):
        SUCCEEDED = "SUCCEEDED", "Успешно"
        FAILED = "FAILED", "Ошибка"

    class FailureReason(models.TextChoices):
        MOCK_DECLINED = "MOCK_DECLINED", "Учебный платёж отклонён. Попробуйте снова."
        PRODUCT_UNAVAILABLE = "PRODUCT_UNAVAILABLE", "Некоторых товаров больше нет в нужном количестве."

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payment_attempts")
    attempt_key = models.UUIDField()
    provider = models.CharField(max_length=16, default="mock")
    result = models.CharField(max_length=9, choices=Result)
    failure_reason = models.CharField(max_length=32, choices=FailureReason, blank=True)
    amount = models.DecimalField(max_digits=28, decimal_places=2)
    currency = models.CharField(max_length=3)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(fields=("order", "attempt_key"), name="payment_attempt_key_unique"),
            models.UniqueConstraint(
                fields=("order",), condition=models.Q(result="SUCCEEDED"), name="payment_one_success_per_order"
            ),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="payment_amount_nonnegative"),
        ]
