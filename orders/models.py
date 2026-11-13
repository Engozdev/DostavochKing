import uuid

from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Создан (ожидает оплаты)"
        CONFIRMED = "CONFIRMED", "Подтверждён"
        HANDED_TO_COURIER = "HANDED_TO_COURIER", "Передан курьеру"
        IN_TRANSIT = "IN_TRANSIT", "В пути"
        DELIVERED = "DELIVERED", "Доставлен"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="client_orders"
    )
    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="courier_orders",
        null=True, blank=True,
    )
    delivery_address = models.TextField(max_length=500)
    total_amount = models.DecimalField(max_digits=28, decimal_places=2)
    currency = models.CharField(max_length=3, default="RUB")
    status = models.CharField(max_length=20, choices=Status, default=Status.CREATED)
    checkout_key = models.UUIDField()
    request_hash = models.CharField(max_length=64)
    assigned_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(fields=("client", "checkout_key"), name="order_client_checkout_key_unique"),
            models.CheckConstraint(condition=models.Q(total_amount__gte=0), name="order_total_nonnegative"),
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    product_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.UniqueConstraint(fields=("order", "product"), name="order_item_product_unique"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="order_item_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="order_item_price_nonnegative"),
        ]

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    from_status = models.CharField(max_length=20, choices=Order.Status, null=True, blank=True)
    to_status = models.CharField(max_length=20, choices=Order.Status)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
