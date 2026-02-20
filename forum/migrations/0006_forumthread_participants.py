# Generated manually for missing forum_forumthread_participants table

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("forum", "0005_forumpost_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="forumthread",
            name="participants",
            field=models.ManyToManyField(
                blank=True,
                related_name="direct_threads",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
