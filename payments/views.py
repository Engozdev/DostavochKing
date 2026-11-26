from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.access import client_required
from orders.models import Order
from orders.services import confirm_mock_payment, get_client_order

from .forms import MockPaymentForm
from .models import PaymentAttempt
from .services import check_yookassa_payment, start_yookassa_payment
from .yookassa import YooKassaError


@client_required
@require_http_methods(["GET", "POST"])
def mock_payment(request, order_id):
    if settings.PAYMENT_PROVIDER != "mock":
        raise Http404

    order = get_client_order(request.user, order_id)
    if order.status != Order.Status.CREATED or order.payment_attempts.filter(provider="yookassa").exists():
        return redirect("orders:detail", order_id=order_id)

    if request.method == "POST":
        form = MockPaymentForm(request.POST)
        if form.is_valid():
            attempt = confirm_mock_payment(request.user, order_id=order_id, **form.cleaned_data)
            if attempt is None or attempt.result == PaymentAttempt.Result.SUCCEEDED:
                return redirect("orders:detail", order_id=order_id)
            return redirect("orders:mock_payment", order_id=order_id)

    context = {
        "order": order,
        "form": MockPaymentForm(initial={"attempt_key": uuid4()}),
        "attempt": order.payment_attempts.first(),
        "success_outcome": PaymentAttempt.Result.SUCCEEDED,
        "failure_outcome": PaymentAttempt.Result.FAILED,
        "form_error": request.method == "POST",
    }
    return render(request, "payments/mock_payment.html", context, status=400 if context["form_error"] else 200)


@client_required
@require_POST
def payment_start(request, order_id):
    if settings.PAYMENT_PROVIDER != "yookassa":
        raise Http404

    try:
        attempt = start_yookassa_payment(request.user, order_id)
    except YooKassaError as error:
        messages.error(request, str(error))
    else:
        if attempt and attempt.result == PaymentAttempt.Result.PENDING and attempt.confirmation_url:
            return redirect(attempt.confirmation_url)
    return redirect("orders:detail", order_id=order_id)


@client_required
@require_GET
def payment_return(request, order_id, attempt_key):
    if settings.PAYMENT_PROVIDER != "yookassa":
        raise Http404

    try:
        check_yookassa_payment(request.user, order_id, attempt_key)
    except YooKassaError as error:
        messages.error(request, str(error))
    return redirect("orders:detail", order_id=order_id)
