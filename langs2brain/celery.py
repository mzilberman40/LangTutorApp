# langs2brain/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "langs2brain.settings")

app = Celery("langs2brain")

# Configuration is now loaded directly from Django settings under the "CELERY" namespace.
# This makes settings.py the single source of truth.
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()