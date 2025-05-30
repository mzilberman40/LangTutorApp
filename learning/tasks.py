"""
Background Celery task for generating example phrases based on a given word.
This task uses an external LLM client to generate phrases and then delegates saving to a service.
"""

import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from learning.models import LexicalUnit
from services.unit2phrases import unit2phrases
from services.save_phrases import parse_and_save_phrases
from ai.client import get_client

logger = logging.getLogger(__name__)


@shared_task
def generate_phrases_async(unit_id: int):
    try:
        unit = LexicalUnit.objects.get(id=unit_id)
    except ObjectDoesNotExist:
        logger.error(f"❌ LexicalUnit with id={unit_id} not found.")
        return

    client = get_client()
    try:
        raw_response = unit2phrases(client, unit.lemma)
        parse_and_save_phrases(raw_response, unit)
        logger.info(f"✅ Successfully generated phrases for unit id={unit_id}")
    except Exception as e:
        logger.error(f"❌ Phrase generation failed for unit id={unit_id}: {e}")
