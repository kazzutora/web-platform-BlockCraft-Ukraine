import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{os.environ.get('ENV', 'dev')}")

app = Celery("blockcraft")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
