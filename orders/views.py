from functools import partial
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from accounts.access import client_required
from payments.models import PaymentAttempt
from payments.services import can_repeat_creation

from .forms import CheckoutForm
from .models import Order
from .services import (
    CancellationConflict,
    CheckoutConflict,
    can_cancel_order,
    cancel_order,
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
    route = "orders:detail" if settings.PAYMENT_PROVIDER == "yookassa" else "orders:mock_payment"
    return redirect(route, order_id=order.pk)


@client_required
@require_safe
def order_list(request):
    return render(request, "orders/list.html", {"orders": list_client_orders(request.user)})


def _render_detail(request, order, *, error="", status=200):
    yookassa_enabled = settings.PAYMENT_PROVIDER == "yookassa"
    attempt = order.payment_attempts.filter(provider="yookassa").first()
    payment_action = ""
    payment_requires_review = False
    can_check_payment = False
    if yookassa_enabled and order.status == Order.Status.CREATED:
        if attempt is None:
            payment_action = "Оплатить картой"
        elif attempt.result == PaymentAttempt.Result.FAILED:
            payment_action = "Повторить оплату"
        elif attempt.result == PaymentAttempt.Result.PENDING:
            if attempt.provider_payment_id:
                payment_action = "Продолжить оплату"
                can_check_payment = True
            elif can_repeat_creation(attempt):
                payment_action = "Повторить подключение к ЮKassa"
            else:
                payment_requires_review = True

    return render(request, "orders/detail.html", {
        "order": order,
        "can_cancel": can_cancel_order(order),
        "error": error,
        "yookassa_enabled": yookassa_enabled,
        "yookassa_attempt": attempt,
        "payment_action": payment_action,
        "payment_requires_review": payment_requires_review,
        "can_check_payment": can_check_payment,
    }, status=status)


@client_required
@require_safe
def detail(request, order_id):
    return _render_detail(request, get_client_order(request.user, order_id))


def _detail_url(order_id):
    return reverse("orders:detail", kwargs={"order_id": order_id})


@partial(client_required, login_next=_detail_url)
@require_POST
def cancel(request, order_id):
    try:
        cancel_order(request.user, order_id=order_id)
    except CancellationConflict as error:
        order = get_client_order(request.user, order_id)
        return _render_detail(request, order, error=str(error), status=409)
    order = get_client_order(request.user, order_id)
    if order.payment_attempts.filter(provider="yookassa", refunds__status="SUCCEEDED").exists():
        messages.success(request, "Заказ отменён. Возврат средств оформлен.")
    else:
        messages.success(request, "Заказ отменён.")
    return redirect("orders:detail", order_id=order_id)
