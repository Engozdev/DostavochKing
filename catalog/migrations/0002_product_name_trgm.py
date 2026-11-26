from django.contrib.postgres.indexes import GinIndex, OpClass
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models
from django.db.models.functions import Upper


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name="product",
            index=GinIndex(
                OpClass(Upper("name"), name="gin_trgm_ops"),
                condition=models.Q(is_active=True),
                name="catalog_active_name_trgm",
            ),
        ),
    ]
