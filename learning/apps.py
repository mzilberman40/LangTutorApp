# In learning/apps.py
from django.apps import AppConfig


class LearningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "learning"

    def ready(self):
        try:
            import learning.signals
        except ImportError:
            pass
