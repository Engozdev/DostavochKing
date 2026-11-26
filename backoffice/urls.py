from django.urls import path

from . import product_views, user_views, views


app_name = "backoffice"
urlpatterns = [
    path("orders/", views.order_list, name="list"),
    path("orders/<uuid:order_id>/", views.detail, name="detail"),
    path("orders/<uuid:order_id>/assign/", views.assign, name="assign"),
    path("products/", product_views.product_list, name="products"),
    path("products/new/", product_views.product_form, name="product_create"),
    path("products/<int:product_id>/edit/", product_views.product_form, name="product_edit"),
    path("products/<int:product_id>/hide/", product_views.set_visibility, {"is_active": False}, name="product_hide"),
    path("products/<int:product_id>/restore/", product_views.set_visibility, {"is_active": True}, name="product_restore"),
    path("users/", user_views.user_list, name="users"),
    path("users/<int:user_id>/block/", user_views.block, name="user_block"),
]
