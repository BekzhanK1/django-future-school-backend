# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0002_initial'),
        ('courses', '0003_initial'),
    ]

    operations = [
        # First, add the new field as nullable
        migrations.AddField(
            model_name='assignment',
            name='course_section',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='courses.coursesection'),
        ),
        # Remove the old field
        migrations.RemoveField(
            model_name='assignment',
            name='course',
        ),
        # Make the new field non-nullable
        migrations.AlterField(
            model_name='assignment',
            name='course_section',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='courses.coursesection'),
        ),
    ]
