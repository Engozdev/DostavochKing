from django.urls import path

from payments.views import mock_payment

from . import views


app_name = "orders"
urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="list"),
    path("orders/<uuid:order_id>/", views.detail, name="detail"),
    path("orders/<uuid:order_id>/mock-payment/", mock_payment, name="mock_payment"),
]
