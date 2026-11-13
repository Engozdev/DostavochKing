import hashlib
import json
from decimal import Decimal

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.access import require_admin, require_client, require_courier
from accounts.models import User
from cart.services import advance_cart_version, get_cart, get_cart_items, lock_cart
from catalog.models import Product
from payments.gateway import MockPaymentGateway
from payments.models import PaymentAttempt

from .models import Order, OrderItem, OrderStatusHistory


QUOTE_SALT = "orders.checkout"


class CheckoutConflict(Exception):
    pass


class DeliveryConflict(Exception):
    pass


def _quote_data(cart, items):
    return {
        "client_id": cart.user_id,
        "cart_id": cart.pk,
        "version": cart.version,
        "items": [
            [item.product_id, item.quantity, str(item.product.price)]
            for item in items
        ],
    }


def _total(items):
    return sum((item.line_total for item in items), Decimal("0.00"))


def checkout_items_available(items):
    return bool(items) and all(item.is_available for item in items)


def get_checkout(client):
    require_client(client)
    cart = get_cart(client)
    items = get_cart_items(cart)
    quote = signing.dumps(_quote_data(cart, items), salt=QUOTE_SALT)
    return items, _total(items), quote


@transaction.atomic
def create_order(client, *, delivery_address, checkout_key, quote):
    require_client(client)
    address = delivery_address.strip()
    if not 1 <= len(address) <= 500:
        raise ValidationError("Введите адрес доставки длиной до 500 символов.")

    try:
        quoted = signing.loads(quote, salt=QUOTE_SALT)
    except signing.BadSignature as error:
        raise CheckoutConflict("Не удалось проверить корзину. Проверьте состав и сумму ещё раз.") from error
    if quoted["client_id"] != client.pk:
        raise CheckoutConflict("Данные корзины устарели. Проверьте состав и сумму ещё раз.")

    payload = json.dumps([address, quoted], ensure_ascii=False, sort_keys=True)
    request_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    cart = lock_cart(client)
    existing = Order.objects.filter(client=client, checkout_key=checkout_key).first()
    if existing:
        if existing.request_hash != request_hash:
            raise CheckoutConflict("Этот запрос уже оформлен с другими данными.")
        return existing

    items = get_cart_items(cart, lock_products=True)
    if _quote_data(cart, items) != quoted:
        raise CheckoutConflict("Корзина или цены изменились. Проверьте состав и сумму ещё раз.")
    if not checkout_items_available(items):
        raise CheckoutConflict("Проверьте наличие товаров и количество в корзине.")

    order = Order.objects.create(
        client=client,
        delivery_address=address,
        total_amount=_total(items),
        checkout_key=checkout_key,
        request_hash=request_hash,
    )
    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            product=item.product,
            product_name=item.product.name,
            unit_price=item.product.price,
            quantity=item.quantity,
        )
        for item in items
    )
    OrderStatusHistory.objects.create(order=order, actor=client, to_status=Order.Status.CREATED)
    cart.items.all().delete()
    advance_cart_version(cart)
    return order


def list_client_orders(client):
    require_client(client)
    return Order.objects.filter(client=client)


def get_client_order(client, order_id):
    return get_object_or_404(list_client_orders(client), pk=order_id)


def list_courier_orders(courier):
    require_courier(courier)
    return Order.objects.filter(courier_id=courier.pk)


def get_courier_order(courier, order_id):
    return get_object_or_404(list_courier_orders(courier), pk=order_id)


def list_operator_orders(operator):
    require_admin(operator)
    return Order.objects.select_related("client", "courier")


def get_operator_order(operator, order_id):
    return get_object_or_404(list_operator_orders(operator), pk=order_id)


def can_assign_courier(order):
    return order.status == Order.Status.CONFIRMED and order.accepted_at is None


def assignment_version(order):
    assignment = f"{order.pk}:{order.courier_id}:{order.assigned_at}"
    return hashlib.sha256(assignment.encode("utf-8")).hexdigest()


@transaction.atomic
def assign_courier(operator, *, order_id, courier, expected_assignment_version=None):
    require_admin(operator)
    order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
    if not can_assign_courier(order):
        raise DeliveryConflict("Курьера можно назначить подтверждённому заказу до его принятия.")
    if not User.objects.filter(pk=courier.pk, role=User.Role.COURIER, is_active=True).exists():
        raise DeliveryConflict("Для назначения выберите активного курьера.")
    if order.courier_id == courier.pk:
        return order
    if expected_assignment_version is not None and assignment_version(order) != expected_assignment_version:
        raise DeliveryConflict("Назначение изменилось. Проверьте текущего курьера и повторите действие.")

    order.courier_id = courier.pk
    order.assigned_at = timezone.now()
    order.save(update_fields=["courier", "assigned_at", "updated_at"])
    return order


@transaction.atomic
def _transition_delivery(courier, *, order_id, source, target):
    order = get_object_or_404(list_courier_orders(courier).select_for_update(), pk=order_id)
    if order.status == target:
        return order
    if order.status != source:
        raise DeliveryConflict("Действие недоступно для текущего статуса заказа.")

    order.status = target
    update_fields = ["status", "updated_at"]
    if target == Order.Status.HANDED_TO_COURIER:
        order.accepted_at = timezone.now()
        update_fields.append("accepted_at")
    order.save(update_fields=update_fields)
    OrderStatusHistory.objects.create(order=order, actor=courier, from_status=source, to_status=target)
    return order


def accept_delivery(courier, *, order_id):
    return _transition_delivery(
        courier, order_id=order_id, source=Order.Status.CONFIRMED, target=Order.Status.HANDED_TO_COURIER
    )


def start_delivery(courier, *, order_id):
    return _transition_delivery(
        courier, order_id=order_id, source=Order.Status.HANDED_TO_COURIER, target=Order.Status.IN_TRANSIT
    )


def complete_delivery(courier, *, order_id):
    return _transition_delivery(
        courier, order_id=order_id, source=Order.Status.IN_TRANSIT, target=Order.Status.DELIVERED
    )


@transaction.atomic
def confirm_mock_payment(client, *, order_id, attempt_key, outcome):
    order = get_object_or_404(list_client_orders(client).select_for_update(), pk=order_id)
    existing = order.payment_attempts.filter(attempt_key=attempt_key).first()
    if existing:
        return existing
    if order.status != Order.Status.CREATED:
        return None

    result = MockPaymentGateway.charge(
        amount=order.total_amount,
        currency=order.currency,
        outcome=outcome,
    )
    failure_reason = PaymentAttempt.FailureReason.MOCK_DECLINED
    if result == PaymentAttempt.Result.SUCCEEDED:
        items = list(order.items.order_by("product_id"))
        products = {
            product.pk: product
            for product in Product.objects.select_for_update()
            .filter(pk__in=[item.product_id for item in items])
            .order_by("pk")
        }
        if not items or any(
            not products[item.product_id].is_active
            or products[item.product_id].stock_quantity < item.quantity
            for item in items
        ):
            result = PaymentAttempt.Result.FAILED
            failure_reason = PaymentAttempt.FailureReason.PRODUCT_UNAVAILABLE
        else:
            for item in items:
                products[item.product_id].stock_quantity -= item.quantity
            Product.objects.bulk_update(products.values(), ["stock_quantity"])
            failure_reason = ""

    attempt = PaymentAttempt.objects.create(
        order=order,
        attempt_key=attempt_key,
        result=result,
        failure_reason=failure_reason,
        amount=order.total_amount,
        currency=order.currency,
    )
    if result == PaymentAttempt.Result.SUCCEEDED:
        order.status = Order.Status.CONFIRMED
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order, from_status=Order.Status.CREATED, to_status=Order.Status.CONFIRMED
        )
    return attempt
