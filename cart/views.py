from decimal import Decimal
from functools import partial

from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe

from accounts.access import client_required
from catalog.models import Product

from . import services
from .forms import AddItemForm, RemoveItemForm, UpdateItemForm
from .models import CartItem


def _render_cart(request, *, errors=(), status=200, fragment=False):
    cart = services.get_cart(request.user)
    items = services.get_cart_items(cart)
    return render(
        request,
        "cart/_contents.html" if fragment else "cart/detail.html",
        {
            "cart": cart,
            "items": items,
            "total": sum((item.line_total for item in items), Decimal("0.00")),
            "can_checkout": bool(items) and all(item.is_available for item in items),
            "errors": errors,
        },
        status=status,
    )


@client_required
@require_safe
def detail(request):
    return _render_cart(request)


def _change_cart(request, product_id, form, operation, *, fragment=False):
    if not form.is_valid():
        errors = [error for field_errors in form.errors.values() for error in field_errors]
        return _render_cart(request, errors=errors, status=400, fragment=fragment)
    try:
        operation(request.user, product_id, **form.cleaned_data)
    except (CartItem.DoesNotExist, Product.DoesNotExist) as error:
        raise Http404 from error
    except services.CartVersionConflict as error:
        return _render_cart(request, errors=[str(error)], status=409, fragment=fragment)
    except services.CartError as error:
        return _render_cart(request, errors=[str(error)], status=400, fragment=fragment)
    if fragment:
        return _render_cart(request, fragment=True)
    return redirect("cart:detail")


def _product_url(product_id):
    return reverse("catalog:detail", kwargs={"product_id": product_id})


def _cart_url(**kwargs):
    return reverse("cart:detail")


@partial(client_required, login_next=_product_url)
@require_POST
def add(request, product_id):
    return _change_cart(request, product_id, AddItemForm(request.POST), services.add_item)


@partial(client_required, login_next=_cart_url)
@require_POST
@transaction.atomic
def update(request, product_id):
    return _change_cart(
        request,
        product_id,
        UpdateItemForm(request.POST),
        services.update_item,
        fragment=request.headers.get("X-Cart-Partial") == "1",
    )


@partial(client_required, login_next=_cart_url)
@require_POST
def remove(request, product_id):
    return _change_cart(request, product_id, RemoveItemForm(request.POST), services.remove_item)
