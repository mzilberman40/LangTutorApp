# Use the project-specified Python version
FROM python:3.13-slim

# Set environment variables to prevent bytecode files and buffer output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Download SpaCy models for all supported languages
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download ru_core_news_sm
RUN python -m spacy download de_core_news_sm
RUN python -m spacy download fr_core_news_sm
RUN python -m spacy download es_core_news_sm
RUN python -m spacy download it_core_news_sm
RUN python -m spacy download pt_core_news_sm
RUN python -m spacy download nl_core_news_sm

# Copy the rest of the application code
COPY . .

# Set the Django settings module environment variable
# This ensures manage.py knows which settings to use
ENV DJANGO_SETTINGS_MODULE=langs2brain.settings

# Collect static files into STATIC_ROOT
# The STATIC_ROOT is defined in settings.py
RUN python manage.py collectstatic --noinput

# Default command for running the application in production
# This will be overridden by the 'command' directive in docker-compose.yml for development
CMD ["gunicorn", "langs2brain.wsgi:application", "--bind", "0.0.0.0:8000"]