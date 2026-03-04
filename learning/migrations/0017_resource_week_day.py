from django.db import migrations, models
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0016_resource_is_visible_to_students"),
    ]

    operations = [
        migrations.AddField(
            model_name="resource",
            name="week_day",
            field=models.IntegerField(
                null=True,
                blank=True,
                validators=[MinValueValidator(0), MaxValueValidator(6)],
                help_text="Day of week within the section (0=Monday, 6=Sunday).",
            ),
        ),
    ]

