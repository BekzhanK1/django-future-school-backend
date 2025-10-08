from django.apps import AppConfig


class LearningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'learning'
    
    def ready(self):
        """Import signals when the app is ready."""
        import learning.signals