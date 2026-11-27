from decimal import Decimal

from accounts.models import User
from catalog.models import Product


def user(email="client@example.test", *, role=User.Role.CLIENT):
    return User.objects.create_user(email=email, password="TestPass123!", name=email.split("@")[0], role=role)


def product(name="Молоко", *, price="120.00", stock=10, active=True):
    return Product.objects.create(
        name=name,
        description="Тестовый товар",
        price=Decimal(price),
        stock_quantity=stock,
        is_active=active,
    )
