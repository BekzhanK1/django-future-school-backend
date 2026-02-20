# Add forum_direct_message notification type for personal messaging

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_notification_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(
                choices=[
                    ('new_assignment', 'New Assignment'),
                    ('assignment_graded', 'Assignment Graded'),
                    ('new_test', 'New Test'),
                    ('test_available', 'Test Available'),
                    ('test_graded', 'Test Graded'),
                    ('forum_question', 'Forum Question'),
                    ('forum_reply', 'Forum Reply'),
                    ('forum_announcement', 'Forum Announcement'),
                    ('forum_direct_message', 'Direct Message'),
                    ('forum_mention', 'Forum Mention'),
                    ('forum_resolved', 'Forum Resolved'),
                    ('manual_grade', 'Manual Grade'),
                    ('new_event', 'New Event'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=32,
            ),
        ),
    ]
