from functools import partial

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe

from accounts.access import courier_required
from orders.models import Order
from orders.services import DeliveryConflict, get_courier_order, list_courier_orders


ORDER_ACTIONS = {
    Order.Status.CONFIRMED: ("delivery:accept", "Принять заказ"),
    Order.Status.HANDED_TO_COURIER: ("delivery:start", "Начать доставку"),
    Order.Status.IN_TRANSIT: ("delivery:complete", "Завершить доставку"),
}


@courier_required
@require_safe
def order_list(request):
    active_orders = []
    completed_orders = []
    for order in list_courier_orders(request.user):
        if order.status == Order.Status.DELIVERED:
            completed_orders.append(order)
        else:
            active_orders.append(order)
    return render(
        request,
        "delivery/list.html",
        {"active_orders": active_orders, "completed_orders": completed_orders},
    )


def _render_detail(request, order, *, error="", status=200):
    action_name, action_label = ORDER_ACTIONS.get(order.status, (None, ""))
    return render(
        request,
        "delivery/detail.html",
        {"order": order, "action_name": action_name, "action_label": action_label, "error": error},
        status=status,
    )


@courier_required
@require_safe
def detail(request, order_id):
    return _render_detail(request, get_courier_order(request.user, order_id))


def _detail_url(order_id, **kwargs):
    return reverse("delivery:detail", kwargs={"order_id": order_id})


@partial(courier_required, login_next=_detail_url)
@require_POST
def change_status(request, order_id, transition):
    try:
        transition(request.user, order_id=order_id)
    except DeliveryConflict as error:
        order = get_courier_order(request.user, order_id)
        return _render_detail(request, order, error=str(error), status=409)
    return redirect("delivery:detail", order_id=order_id)
