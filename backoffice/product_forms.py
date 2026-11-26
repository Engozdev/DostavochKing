from io import BytesIO
from uuid import uuid4

from django import forms
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from catalog.models import Product


PHOTO_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
MAX_PHOTO_SIZE = 5 * 1024 * 1024
MAX_PHOTO_SIDE = 4096


class ProductForm(forms.ModelForm):
    photo = forms.FileField(
        label="Фото товара",
        required=False,
        help_text="JPEG, PNG или WebP до 5 МБ. Максимальный размер — 4096 × 4096 пикселей.",
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}),
    )
    remove_image = forms.BooleanField(
        label="Убрать загруженное фото",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    version = forms.CharField(max_length=64, widget=forms.HiddenInput)

    class Meta:
        model = Product
        fields = ("name", "description", "price", "stock_quantity", "photo", "remove_image", "version")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "stock_quantity": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            del self.fields["version"]
        if not self.instance.uploaded_image:
            del self.fields["remove_image"]

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        if photo is None:
            return None
        if photo.size > MAX_PHOTO_SIZE:
            raise forms.ValidationError("Размер файла не должен превышать 5 МБ.")

        try:
            with Image.open(photo, formats=tuple(PHOTO_EXTENSIONS)) as source:
                if max(source.size) > MAX_PHOTO_SIDE:
                    raise forms.ValidationError("Сторона изображения не должна превышать 4096 пикселей.")
                image_format = source.format
                source.verify()

            # Encode decoded pixels so that extra bytes and source metadata are not served to browsers.
            photo.seek(0)
            with Image.open(photo, formats=(image_format,)) as source, BytesIO() as output:
                oriented = ImageOps.exif_transpose(source)
                has_alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                mode = "RGBA" if image_format != "JPEG" and has_alpha else "RGB"
                image = oriented.convert(mode)
                image.info.clear()
                image.save(output, format=image_format)
                return ContentFile(output.getvalue(), name=f"{uuid4().hex}{PHOTO_EXTENSIONS[image_format]}")
        except (Image.DecompressionBombError, OSError, SyntaxError, ValueError) as error:
            raise forms.ValidationError("Загрузите корректное изображение в формате JPEG, PNG или WebP.") from error

    def clean(self):
        data = super().clean()
        if data.get("photo") and data.get("remove_image"):
            self.add_error("remove_image", "Выберите одно действие с фотографией.")
        return data
