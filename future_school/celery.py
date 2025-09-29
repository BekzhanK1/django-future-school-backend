from __future__ import annotations

import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "future_school.settings")

celery_app = Celery("future_school")

# Read config from Django settings, using CELERY_ namespace
celery_app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in installed apps
celery_app.autodiscover_tasks()


@celery_app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")





