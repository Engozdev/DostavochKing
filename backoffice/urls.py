from django.urls import path

from . import views


app_name = "backoffice"
urlpatterns = [
    path("", views.order_list, name="list"),
    path("<uuid:order_id>/", views.detail, name="detail"),
    path("<uuid:order_id>/assign/", views.assign, name="assign"),
]
