from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_product_name_trgm")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="uploaded_image",
            field=models.ImageField(blank=True, upload_to="products/", verbose_name="загруженное фото"),
        ),
    ]
