# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .


# -------- collect static files --------
# STATIC_ROOT must exist in settings.py (e.g. STATIC_ROOT = "/app/static/")
# If DJANGO_SETTINGS_MODULE isn’t picked up automatically, set it here:
# ENV DJANGO_SETTINGS_MODULE=langs2brain.settings
RUN python manage.py collectstatic --noinput
# --------------------------------------


CMD ["gunicorn", "langs2brain.wsgi:application", "--bind", "0.0.0.0:8000"]
