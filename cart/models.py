from django.conf import settings
from django.db import models


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    version = models.PositiveBigIntegerField(default=0)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("cart", "product"), name="cart_unique_product"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="cart_positive_quantity"),
        ]

    @property
    def line_total(self):
        return self.product.price * self.quantity

    @property
    def is_available(self):
        return self.product.is_active and self.quantity <= self.product.stock_quantity
