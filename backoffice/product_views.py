import json
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from accounts.access import admin_required
from catalog.models import Product

from .product_forms import ProductForm


logger = logging.getLogger(__name__)


def _product_version(product):
    state = json.dumps([
        product.pk, product.name, product.description, str(product.price), product.stock_quantity,
        product.is_active, product.image_path, product.uploaded_image.name,
    ])
    return salted_hmac("backoffice.product", state, algorithm="sha256").hexdigest()


def _render_product_form(request, product, form=None, *, error="", status=200):
    if form is None:
        initial = {"version": _product_version(product)} if product else None
        form = ProductForm(instance=product, initial=initial)
    return render(request, "backoffice/product_form.html", {
        "product": product,
        "form": form,
        "error": error,
    }, status=status)


@admin_required
@require_safe
def product_list(request):
    products = Product.objects.order_by("name", "pk")
    page_obj = Paginator(products, 25).get_page(request.GET.get("page"))
    return render(request, "backoffice/products.html", {"page_obj": page_obj})


@admin_required
@require_http_methods(["GET", "POST"])
def product_form(request, product_id=None):
    if request.method == "GET":
        product = get_object_or_404(Product, pk=product_id) if product_id is not None else None
        return _render_product_form(request, product)

    uploaded_name = ""
    previous_name = ""
    product = None
    form = None
    try:
        with transaction.atomic():
            if product_id is not None:
                product = get_object_or_404(Product.objects.select_for_update(), pk=product_id)
                previous_name = product.uploaded_image.name
                version = request.POST.get("version", "")
                if not constant_time_compare(_product_version(product), version):
                    return _render_product_form(
                        request, product, status=409,
                        error="Товар изменился. Проверьте актуальные данные и внесите изменения снова.",
                    )

            form = ProductForm(request.POST, request.FILES, instance=product)
            if not form.is_valid():
                return _render_product_form(request, product, form, status=400)

            updated_product = form.save(commit=False)
            image_field = updated_product.uploaded_image
            if photo := form.cleaned_data["photo"]:
                image_field.save(photo.name, photo, save=False)
                uploaded_name = image_field.name
            elif form.cleaned_data.get("remove_image"):
                updated_product.uploaded_image = ""
            updated_product.save()

            if previous_name and previous_name != updated_product.uploaded_image.name:
                transaction.on_commit(lambda: image_field.storage.delete(previous_name), robust=True)
    except (DatabaseError, OSError):
        logger.exception("Could not save product %s", product_id)
        if uploaded_name:
            try:
                image_field.storage.delete(uploaded_name)
            except OSError:
                logger.exception("Could not remove failed product upload %s", uploaded_name)
        if product is not None and form is not None:
            product.uploaded_image = previous_name
        return _render_product_form(
            request, product, form, status=503, error="Не удалось сохранить товар. Попробуйте ещё раз.",
        )

    messages.success(request, "Товар сохранён." if product_id is not None else "Товар добавлен.")
    return redirect("backoffice:products")


@admin_required
@require_POST
def set_visibility(request, product_id, *, is_active):
    if not Product.objects.filter(pk=product_id).update(is_active=is_active):
        raise Http404
    messages.success(request, "Товар снова виден в каталоге." if is_active else "Товар скрыт из каталога.")
    return redirect("backoffice:products")
