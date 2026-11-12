from functools import partial

from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe

from accounts.access import admin_required
from accounts.models import User
from orders.models import Order
from orders.services import (
    DeliveryConflict,
    assign_courier,
    assignment_version,
    can_assign_courier,
    get_operator_order,
    list_operator_orders,
)

from .forms import CourierAssignmentForm


@admin_required
@require_safe
def order_list(request):
    orders = list_operator_orders(request.user)
    selected_status = request.GET.get("status", "")
    if selected_status in Order.Status.values:
        orders = orders.filter(status=selected_status)
    else:
        selected_status = ""
    page_obj = Paginator(orders, 25).get_page(request.GET.get("page"))
    return render(request, "backoffice/list.html", {
        "page_obj": page_obj,
        "selected_status": selected_status,
        "status_choices": Order.Status.choices,
    })


def _render_detail(request, order, *, form=None, error="", status=200):
    if not can_assign_courier(order):
        form = None
    elif form is None:
        initial = {"assignment_version": assignment_version(order)}
        courier = order.courier
        if courier and courier.is_active and courier.role == User.Role.COURIER:
            initial["courier"] = courier.pk
        form = CourierAssignmentForm(initial=initial)

    context = {
        "order": order,
        "form": form,
        "has_eligible_couriers": form is not None and form.fields["courier"].queryset.exists(),
        "error": error,
    }
    return render(request, "backoffice/detail.html", context, status=status)


@admin_required
@require_safe
def detail(request, order_id):
    return _render_detail(request, get_operator_order(request.user, order_id))


def _detail_url(order_id):
    return reverse("backoffice:detail", kwargs={"order_id": order_id})


@partial(admin_required, login_next=_detail_url)
@require_POST
def assign(request, order_id):
    form = CourierAssignmentForm(request.POST)
    if not form.is_valid():
        order = get_operator_order(request.user, order_id)
        if version_errors := form.errors.get("assignment_version"):
            return _render_detail(request, order, error=version_errors[0], status=400)
        error = "" if can_assign_courier(order) else form.errors["courier"][0]
        return _render_detail(request, order, form=form, error=error, status=400)

    try:
        assign_courier(
            request.user,
            order_id=order_id,
            courier=form.cleaned_data["courier"],
            expected_assignment_version=form.cleaned_data["assignment_version"],
        )
    except DeliveryConflict as error:
        order = get_operator_order(request.user, order_id)
        return _render_detail(request, order, error=str(error), status=409)
    return redirect("backoffice:detail", order_id=order_id)
