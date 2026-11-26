from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models.functions import Upper


class Product(models.Model):
    name = models.CharField("название", max_length=200)
    description = models.TextField("описание")
    price = models.DecimalField("цена", max_digits=12, decimal_places=2)
    stock_quantity = models.PositiveIntegerField("остаток", default=0)
    image_path = models.CharField("путь к изображению", max_length=255, blank=True)
    uploaded_image = models.ImageField("загруженное фото", upload_to="products/", blank=True)
    is_active = models.BooleanField("активен", default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="catalog_nonnegative_price"),
        ]
        indexes = [
            GinIndex(
                OpClass(Upper("name"), name="gin_trgm_ops"),
                condition=models.Q(is_active=True),
                name="catalog_active_name_trgm",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        return self.is_active and self.stock_quantity > 0
