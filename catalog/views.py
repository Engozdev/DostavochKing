from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from .models import Product


@require_safe
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by("name", "pk")
    return render(request, "catalog/product_list.html", {"products": products})


@require_safe
def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    return render(request, "catalog/product_detail.html", {"product": product})
