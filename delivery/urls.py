from django.urls import path

from orders.services import accept_delivery, complete_delivery, start_delivery

from . import views


app_name = "delivery"
urlpatterns = [
    path("", views.order_list, name="list"),
    path("<uuid:order_id>/", views.detail, name="detail"),
    path("<uuid:order_id>/accept/", views.change_status, {"transition": accept_delivery}, name="accept"),
    path("<uuid:order_id>/start/", views.change_status, {"transition": start_delivery}, name="start"),
    path("<uuid:order_id>/complete/", views.change_status, {"transition": complete_delivery}, name="complete"),
]
