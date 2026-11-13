from django.urls import path

from . import views


app_name = "cart"
urlpatterns = [
    path("", views.detail, name="detail"),
    path("items/<int:product_id>/add/", views.add, name="add"),
    path("items/<int:product_id>/update/", views.update, name="update"),
    path("items/<int:product_id>/remove/", views.remove, name="remove"),
]
