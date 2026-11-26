from django.urls import path

from payments.views import mock_payment, payment_return, payment_start

from . import views


app_name = "orders"
urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="list"),
    path("orders/<uuid:order_id>/", views.detail, name="detail"),
    path("orders/<uuid:order_id>/cancel/", views.cancel, name="cancel"),
    path("orders/<uuid:order_id>/mock-payment/", mock_payment, name="mock_payment"),
    path("orders/<uuid:order_id>/payment/", payment_start, name="payment_start"),
    path("orders/<uuid:order_id>/payment/<uuid:attempt_key>/return/", payment_return, name="payment_return"),
]
