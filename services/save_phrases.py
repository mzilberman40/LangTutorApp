# services/save_phrases.py

import json
import logging
from learning.models import Phrase, LexicalUnit, PhraseTranslation

logger = logging.getLogger(__name__)


def parse_and_save_phrases(raw_response, lexical_unit):
    try:
        data = json.loads(raw_response)
        for item in data:
            native = item.get(lexical_unit.language)
            target = item.get(lexical_unit.translation_language)
            cefr = item.get("CEFR", "B2")

            if not native or not target:
                logger.warning(f"⚠️ Skipping incomplete phrase: {item}")
                continue

            phrase = Phrase.objects.create(cefr=cefr)
            PhraseTranslation.objects.create(
                phrase=phrase,
                language=lexical_unit.language,
                text=native,
            )
            PhraseTranslation.objects.create(
                phrase=phrase,
                language=lexical_unit.translation_language,
                text=target,
            )
        logger.info(
            f"✅ Saved {len(data)} phrases for LexicalUnit '{lexical_unit.lemma}'"
        )
    except Exception as e:
        logger.error(f"❌ Failed to parse/save phrases: {e}")
