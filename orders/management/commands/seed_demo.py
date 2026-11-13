import os
from decimal import Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import Product
from orders.models import Order, OrderItem, OrderStatusHistory
from payments.models import PaymentAttempt


DEMO_EMAIL = "demo@example.test"
DEMO_COURIER_EMAIL = "courier@example.test"
DEMO_PRODUCTS = (
    ("apples", "Яблоки Гренни Смит", "Хрустящие зелёные яблоки с кислинкой, 1 кг.", "189.00", 24),
    ("bread", "Хлеб на закваске", "Пшеничный хлеб с хрустящей корочкой, 450 г.", "149.00", 8),
    ("milk", "Молоко цельное", "Пастеризованное цельное молоко, 900 мл.", "119.00", 15),
    ("strawberries", "Клубника свежая", "Спелая клубника, 250 г.", "299.00", 0),
)
DEMO_STATUSES = (
    Order.Status.CREATED,
    Order.Status.CONFIRMED,
    Order.Status.HANDED_TO_COURIER,
    Order.Status.IN_TRANSIT,
    Order.Status.DELIVERED,
)


def demo_uuid(label):
    return uuid5(NAMESPACE_URL, f"dostavochking/seed_demo/{label}")


def get_demo_user(email, name, role, password=None):
    user, created = User.objects.select_for_update().get_or_create(
        email=email, defaults={"name": name, "role": role}
    )
    if user.role != role:
        raise CommandError(f"У учётной записи {email} другая роль.")
    if created or (password and not user.has_usable_password()):
        if password:
            try:
                validate_password(password, user)
            except ValidationError as exc:
                raise CommandError(" ".join(exc.messages)) from exc
        user.set_password(password)
        user.save(update_fields=["password"])
    return user


def create_demo_order(client, courier, product, step, *, ready_for_pickup=False):
    status = DEMO_STATUSES[step]
    fixture_key = "assigned-confirmed" if ready_for_pickup else status
    assigned_at = timezone.now() if step >= 2 or ready_for_pickup else None
    order, created = Order.objects.get_or_create(
        id=demo_uuid(fixture_key),
        defaults={
            "client": client,
            "courier": courier if assigned_at else None,
            "assigned_at": assigned_at,
            "accepted_at": assigned_at if step >= 2 else None,
            "delivery_address": "Москва, Учебная улица, дом 1, квартира 2",
            "total_amount": product.price,
            "status": status,
            "checkout_key": demo_uuid(f"checkout/{fixture_key}"),
            "request_hash": sha256(f"seed_demo/{fixture_key}".encode()).hexdigest(),
        },
    )
    if not created:
        return

    OrderItem.objects.create(
        order=order, product=product, product_name=product.name, unit_price=product.price, quantity=1
    )
    history = DEMO_STATUSES[: step + 1]
    previous = None
    for next_status in history:
        actor = {
            Order.Status.CREATED: client,
            Order.Status.CONFIRMED: None,
        }.get(next_status, courier)
        OrderStatusHistory.objects.create(
            order=order, actor=actor, from_status=previous, to_status=next_status
        )
        previous = next_status
    if step > 0:
        PaymentAttempt.objects.create(
            order=order,
            attempt_key=demo_uuid(f"payment/{fixture_key}"),
            result=PaymentAttempt.Result.SUCCEEDED,
            amount=order.total_amount,
            currency=order.currency,
        )


class Command(BaseCommand):
    help = "Загрузить демонстрационные товары и заказы для локального запуска."

    @transaction.atomic
    def handle(self, *args, **options):
        client = get_demo_user(
            DEMO_EMAIL, "Демо-клиент", User.Role.CLIENT, os.environ.get("DEMO_CLIENT_PASSWORD") or None
        )
        courier = get_demo_user(
            DEMO_COURIER_EMAIL,
            "Демо-курьер",
            User.Role.COURIER,
            os.environ.get("DEMO_COURIER_PASSWORD") or None,
        )
        products = []
        for image, name, description, price, stock in DEMO_PRODUCTS:
            product, _ = Product.objects.get_or_create(
                image_path=f"img/{image}.jpg",
                defaults={
                    "name": name, "description": description, "price": Decimal(price), "stock_quantity": stock
                },
            )
            products.append(product)

        for step in range(len(DEMO_STATUSES)):
            create_demo_order(client, courier, products[step % 3], step)
        create_demo_order(client, courier, products[0], step=1, ready_for_pickup=True)

        self.stdout.write(self.style.SUCCESS(f"Демо-данные готовы. Клиент {DEMO_EMAIL}, курьер {DEMO_COURIER_EMAIL}."))
        if not client.has_usable_password():
            self.stdout.write("Для входа клиента задайте DEMO_CLIENT_PASSWORD и повторите команду.")
        if not courier.has_usable_password():
            self.stdout.write("Для входа курьера задайте DEMO_COURIER_PASSWORD и повторите команду.")
