from django.urls import include, path
from django.views.generic import RedirectView

from .views import health


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="catalog:list"), name="home"),
    path("auth/", include("accounts.urls")),
    path("products/", include("catalog.urls")),
    path("cart/", include("cart.urls")),
    path("courier/orders/", include("delivery.urls")),
    path("operator/orders/", include("backoffice.urls")),
    path("", include("orders.urls")),
    path("health/", health, name="health"),
]
