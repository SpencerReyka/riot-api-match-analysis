from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApplicationSecret",
            fields=[
                (
                    "name",
                    models.CharField(
                        editable=False, max_length=64, primary_key=True, serialize=False
                    ),
                ),
                ("encrypted_value", models.TextField(editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by",
                    models.CharField(blank=True, editable=False, max_length=150),
                ),
            ],
        ),
    ]
