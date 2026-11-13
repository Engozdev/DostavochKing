from uuid import uuid4

from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_safe

from accounts.access import client_required

from .forms import CheckoutForm
from .services import (
    CheckoutConflict,
    checkout_items_available,
    create_order,
    get_checkout,
    get_client_order,
    list_client_orders,
)


def _render_checkout(request, *, invalid_form=None, address="", error="", status=200):
    items, total_amount, quote = get_checkout(request.user)
    form_data = {"checkout_key": uuid4(), "quote": quote, "delivery_address": address}
    if invalid_form is None:
        form = CheckoutForm(initial=form_data)
    else:
        form_data["delivery_address"] = invalid_form["delivery_address"].value()
        form = CheckoutForm(data=form_data)
    context = {
        "form": form,
        "items": items,
        "total_amount": total_amount,
        "can_checkout": checkout_items_available(items),
        "error": error,
    }
    return render(request, "orders/checkout.html", context, status=status)


@client_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    if request.method == "GET":
        return _render_checkout(request)

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        error = ""
        if form.errors.keys() & {"checkout_key", "quote"}:
            error = "Данные формы устарели. Проверьте заказ и попробуйте снова."
        return _render_checkout(request, invalid_form=form, error=error, status=400)

    try:
        order = create_order(request.user, **form.cleaned_data)
    except CheckoutConflict as error:
        return _render_checkout(
            request,
            address=form.cleaned_data["delivery_address"],
            error=str(error),
            status=409,
        )
    return redirect("orders:mock_payment", order_id=order.pk)


@client_required
@require_safe
def order_list(request):
    return render(request, "orders/list.html", {"orders": list_client_orders(request.user)})


@client_required
@require_safe
def detail(request, order_id):
    order = get_client_order(request.user, order_id)
    return render(request, "orders/detail.html", {"order": order})
