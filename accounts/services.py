from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404

from orders.models import Order

from .access import require_admin
from .models import User


class UserBlockConflict(Exception):
    def __init__(self, message, *, orders=()):
        super().__init__(message)
        self.orders = orders


def lock_users(*user_ids):
    # Keep foreign-key checks on users compatible with locks for account changes.
    return User.objects.select_for_update(no_key=True).filter(pk__in=user_ids).order_by("pk").in_bulk()


@transaction.atomic
def block_user(operator, *, user_id):
    require_admin(operator)
    users = lock_users(operator.pk, user_id)
    current_operator = users.get(operator.pk)
    if current_operator is None:
        raise PermissionDenied
    require_admin(current_operator)

    user = users.get(user_id)
    if user is None:
        raise Http404
    if user.pk == current_operator.pk:
        raise UserBlockConflict("Нельзя заблокировать свою учётную запись.")
    if not user.is_active:
        return user

    if user.role == User.Role.COURIER:
        orders = list(Order.objects.filter(
            courier=user,
            status__in=(Order.Status.HANDED_TO_COURIER, Order.Status.IN_TRANSIT),
        ).only("status"))
        if orders:
            raise UserBlockConflict("Сначала курьеру нужно завершить начатые доставки.", orders=orders)

    user.is_active = False
    user.save(update_fields=["is_active"])
    return user
