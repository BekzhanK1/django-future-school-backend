# Generated manually: multiple file attachments per forum post

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("forum", "0007_alter_forumthread_subject_group_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ForumPostAttachment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "file",
                    models.FileField(upload_to="forum_posts/attachments/%Y/%m/"),
                ),
                ("position", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="forum.forumpost",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
            },
        ),
    ]
