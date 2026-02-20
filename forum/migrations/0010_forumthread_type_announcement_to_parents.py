# Generated: add announcement_to_parents choice for teacher → all parents

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0009_forumthread_archived'),
    ]

    operations = [
        migrations.AlterField(
            model_name='forumthread',
            name='type',
            field=models.CharField(
                choices=[
                    ('question', 'Question'),
                    ('announcement', 'Announcement'),
                    ('announcement_to_parents', 'Announcement to parents'),
                    ('direct_message', 'Direct Message'),
                ],
                default='question',
                max_length=32,
            ),
        ),
    ]
