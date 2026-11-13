from uuid import uuid4

from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.access import client_required
from orders.models import Order
from orders.services import confirm_mock_payment, get_client_order

from .forms import MockPaymentForm
from .models import PaymentAttempt


@client_required
@require_http_methods(["GET", "POST"])
def mock_payment(request, order_id):
    if request.method == "POST":
        form = MockPaymentForm(request.POST)
        if form.is_valid():
            attempt = confirm_mock_payment(request.user, order_id=order_id, **form.cleaned_data)
            if attempt is None or attempt.result == PaymentAttempt.Result.SUCCEEDED:
                return redirect("orders:detail", order_id=order_id)
            return redirect("orders:mock_payment", order_id=order_id)

    order = get_client_order(request.user, order_id)
    if order.status != Order.Status.CREATED:
        return redirect("orders:detail", order_id=order_id)

    context = {
        "order": order,
        "form": MockPaymentForm(initial={"attempt_key": uuid4()}),
        "attempt": order.payment_attempts.first(),
        "success_outcome": PaymentAttempt.Result.SUCCEEDED,
        "failure_outcome": PaymentAttempt.Result.FAILED,
        "form_error": request.method == "POST",
    }
    return render(request, "payments/mock_payment.html", context, status=400 if context["form_error"] else 200)
