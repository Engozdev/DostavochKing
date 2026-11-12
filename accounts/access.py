from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache

from .models import User


def _require_role(user, role):
    if not user.is_authenticated or not user.is_active or user.role != role:
        raise PermissionDenied


def require_client(user):
    _require_role(user, User.Role.CLIENT)


def require_courier(user):
    _require_role(user, User.Role.COURIER)


def require_admin(user):
    _require_role(user, User.Role.ADMIN)


def _role_required(view, require_role, *, login_next=None):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if login_next is not None and not request.user.is_authenticated:
            return redirect_to_login(login_next(*args, **kwargs))
        require_role(request.user)
        return view(request, *args, **kwargs)

    if login_next is None:
        wrapped = login_required(wrapped)
    return never_cache(wrapped)


def client_required(view, *, login_next=None):
    return _role_required(view, require_client, login_next=login_next)


def courier_required(view, *, login_next=None):
    return _role_required(view, require_courier, login_next=login_next)


def admin_required(view, *, login_next=None):
    return _role_required(view, require_admin, login_next=login_next)
