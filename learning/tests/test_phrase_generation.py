import logging
from celery import shared_task
from ai.client import get_client

from services.unit2phrases import unit2phrases
from services.save_phrases import parse_and_save_phrases
from learning.models import LexicalUnit

logger = logging.getLogger(__name__)


@shared_task
def generate_phrases_async(unit_id):
    logger.debug(f"🚀 Starting Celery task: generate_phrases_async({unit_id})")

    try:
        unit = LexicalUnit.objects.get(pk=unit_id)
        logger.debug(f"🔍 LexicalUnit found: {unit.lemma} [{unit.language}]")
    except LexicalUnit.DoesNotExist:
        logger.error(f"❌ LexicalUnit with id={unit_id} not found.")
        return

    client = get_client()

    try:
        response = unit2phrases(
            client=client, lemma=unit.lemma, lang1="ru", lang2="en_GB", cefr="B2"
        )
        logger.debug(f"📥 LLM raw response: {response[:100]}...")
    except Exception as e:
        logger.error(f"❌ Failed to generate phrases: {e}")
        return

    try:
        created_phrases = parse_and_save_phrases(response, unit)
        logger.debug(f"✅ Saved {len(created_phrases)} phrases for word '{unit.lemma}'")
    except Exception as e:
        logger.error(f"❌ Failed to parse/save phrases: {e}")

    logger.debug(f"🏁 Finished Celery task: generate_phrases_async({unit_id})")
