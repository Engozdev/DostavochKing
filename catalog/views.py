from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from accounts.models import User

from .models import Product


@require_safe
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by("name", "pk")
    search_query = request.GET.get("q", "").strip()
    if "\x00" in search_query:
        products = products.none()
    elif search_query:
        products = products.filter(name__icontains=search_query)

    return render(request, "catalog/product_list.html", {
        "page_obj": Paginator(products, 24).get_page(request.GET.get("page")),
        "search_query": search_query,
    })


@require_safe
def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    return render(request, "catalog/product_detail.html", {"product": product})


@require_safe
@never_cache
def product_image(request, product_id):
    products = Product.objects.exclude(uploaded_image="")
    if not (request.user.is_active and request.user.role == User.Role.ADMIN):
        products = products.filter(is_active=True)
    product = get_object_or_404(products, pk=product_id)
    try:
        image = product.uploaded_image.open("rb")
    except FileNotFoundError as error:
        raise Http404 from error
    return FileResponse(image)
