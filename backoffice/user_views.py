from functools import partial

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_safe

from accounts.access import admin_required
from accounts.models import User
from accounts.services import UserBlockConflict, block_user


def _render_user_list(request, *, error=None, status=200):
    users = User.objects.order_by("name", "email", "pk")
    page = Paginator(users, 25).get_page(request.GET.get("page"))
    return render(request, "backoffice/users.html", {"page_obj": page, "error": error}, status=status)


@admin_required
@require_safe
def user_list(request):
    return _render_user_list(request)


def _list_url(user_id):
    return reverse("backoffice:users")


@partial(admin_required, login_next=_list_url)
@require_POST
def block(request, user_id):
    try:
        account = block_user(request.user, user_id=user_id)
    except UserBlockConflict as error:
        return _render_user_list(request, error=error, status=409)

    messages.success(request, f"Учётная запись {account.email} заблокирована.")
    page = request.GET.get("page")
    return redirect(reverse("backoffice:users", query={"page": page} if page else None))
