import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def generate_phrases_async(word_id):
    logger.info(f"📦 Celery task received: generate_phrases_async({word_id})")
