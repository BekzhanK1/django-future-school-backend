from django.contrib.auth.management.commands.createsuperuser import Command as BaseCommand


class Command(BaseCommand):
    help = 'Create a superuser with superadmin role (default)'

    def handle(self, *args, **options):
        # The UserManager.create_superuser will automatically set role=SUPERADMIN
        super().handle(*args, **options)
