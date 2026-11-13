from django.db import transaction

from accounts.access import require_client
from catalog.models import Product

from .models import Cart, CartItem


class CartError(ValueError):
    pass


class CartVersionConflict(CartError):
    pass


def get_cart(client):
    require_client(client)
    return Cart.objects.filter(user=client).first() or Cart(user=client)


def get_cart_items(cart, *, lock_products=False):
    if cart.pk is None:
        return []
    items = cart.items.select_related("product").order_by("product_id")
    if lock_products:
        items = items.select_for_update(of=("product",))
    return list(items)


def lock_cart(client):
    require_client(client)
    cart, _ = Cart.objects.get_or_create(user=client)
    return Cart.objects.select_for_update().get(pk=cart.pk)


def _require_version(cart, version):
    if cart.version != version:
        raise CartVersionConflict("Корзина изменилась. Проверьте её состав и повторите действие.")


def _require_available_quantity(product, quantity):
    if quantity < 1:
        raise CartError("Количество должно быть не меньше одного.")
    if not product.is_available:
        raise CartError("Товар сейчас недоступен.")
    if quantity > product.stock_quantity:
        raise CartError(f"«{product.name}» в наличии: {product.stock_quantity} шт.")


def advance_cart_version(cart):
    cart.version += 1
    cart.save(update_fields=["version"])


@transaction.atomic
def add_item(client, product_id, quantity):
    if quantity < 1:
        raise CartError("Количество должно быть не меньше одного.")
    cart = lock_cart(client)
    product = Product.objects.select_for_update().get(pk=product_id)
    item = cart.items.filter(product=product).first()
    new_quantity = quantity + (item.quantity if item else 0)
    _require_available_quantity(product, new_quantity)
    if item:
        item.quantity = new_quantity
        item.save(update_fields=["quantity"])
    else:
        cart.items.create(product=product, quantity=new_quantity)
    advance_cart_version(cart)


@transaction.atomic
def update_item(client, product_id, quantity, version):
    cart = lock_cart(client)
    _require_version(cart, version)
    item = cart.items.get(product_id=product_id)
    product = Product.objects.select_for_update().get(pk=product_id)
    _require_available_quantity(product, quantity)
    if item.quantity != quantity:
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        advance_cart_version(cart)


@transaction.atomic
def remove_item(client, product_id, version):
    cart = lock_cart(client)
    _require_version(cart, version)
    item = cart.items.get(product_id=product_id)
    item.delete()
    advance_cart_version(cart)
