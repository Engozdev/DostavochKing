from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods

from .forms import EMAIL_EXISTS, EmailAuthenticationForm, RegistrationForm
from .models import User


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("catalog:list")
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            if not User.objects.filter(email__iexact=form.cleaned_data["email"]).exists():
                raise
            form.add_error("email", EMAIL_EXISTS)
        else:
            return redirect("accounts:login")
    return render(request, "accounts/register.html", {"form": form})


class RoleLoginView(auth_views.LoginView):
    def get_default_redirect_url(self):
        if self.request.user.role == User.Role.ADMIN:
            return reverse("backoffice:list")
        if self.request.user.role == User.Role.COURIER:
            return reverse("delivery:list")
        return super().get_default_redirect_url()


login = RoleLoginView.as_view(
    template_name="accounts/login.html",
    authentication_form=EmailAuthenticationForm,
    redirect_authenticated_user=True,
    next_page=reverse_lazy("catalog:list"),
)

logout = login_required(auth_views.LogoutView.as_view(next_page=reverse_lazy("catalog:list")))
