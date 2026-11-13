from django.db import models


class Product(models.Model):
    name = models.CharField("название", max_length=200)
    description = models.TextField("описание")
    price = models.DecimalField("цена", max_digits=12, decimal_places=2)
    stock_quantity = models.PositiveIntegerField("остаток", default=0)
    image_path = models.CharField("путь к изображению", max_length=255, blank=True)
    is_active = models.BooleanField("активен", default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="catalog_nonnegative_price"),
        ]

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        return self.is_active and self.stock_quantity > 0
