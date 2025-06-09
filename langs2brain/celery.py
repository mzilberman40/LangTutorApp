import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "langs2brain.settings")

app = Celery("langs2brain")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ✅ Укажи Redis как брокер
app.conf.broker_url = "redis://redis:6379/0"

# ✅ ADD THIS LINE to tell Celery where to store task results.
app.conf.result_backend = "redis://redis:6379/1"
