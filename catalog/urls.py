from django.urls import path

from . import views


app_name = "catalog"
urlpatterns = [
    path("", views.product_list, name="list"),
    path("<int:product_id>/", views.product_detail, name="detail"),
    path("<int:product_id>/image/", views.product_image, name="image"),
]
