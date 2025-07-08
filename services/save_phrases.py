# services/save_phrases.py
import json
import logging
from learning.models import Phrase, LexicalUnit, PhraseTranslation

logger = logging.getLogger(__name__)


def parse_and_save_phrases(
    raw_response: str,
    lexical_unit: LexicalUnit,
    source_language: str,
    target_language: str,
):
    """
    Parses the JSON response and saves the data.
    Uses standardised 'source_language' and 'target_language' parameters.
    """
    created_count = 0
    if not raw_response:
        logger.warning(f"Received empty response for '{lexical_unit.lemma}'.")
        return created_count

    try:
        data = json.loads(raw_response)
        phrase_pairs = []

        if isinstance(data, dict):
            phrase_pairs = data.get("phrases", [])
        elif isinstance(data, list):
            phrase_pairs = data
        else:
            logger.error(
                f"LLM response is not a list or a dict with a 'phrases' key. Response: {raw_response}"
            )
            return created_count

        if not isinstance(phrase_pairs, list):
            logger.error(
                f"Data under 'phrases' key is not a list. Response: {raw_response}"
            )
            return created_count

        for item in phrase_pairs:
            original_text = item.get("original_phrase")
            translated_text = item.get("translated_phrase")
            cefr = item.get("cefr")

            if not all([original_text, translated_text, cefr]):
                logger.warning(
                    f"Skipping phrase pair for '{lexical_unit.lemma}' due to missing data: {item}"
                )
                continue

            try:
                phrase_original = Phrase.objects.create(
                    text=original_text, language=source_language, cefr=cefr
                )
                phrase_original.units.add(lexical_unit)

                phrase_translated = Phrase.objects.create(
                    text=translated_text, language=target_language, cefr=cefr
                )

                PhraseTranslation.objects.create(
                    source_phrase=phrase_original, target_phrase=phrase_translated
                )
                created_count += 1
            except Exception as e_inner:
                logger.error(
                    f"Failed to save a phrase pair for '{lexical_unit.lemma}': {e_inner}",
                    exc_info=True,
                )

        if created_count > 0:
            logger.info(
                f"Successfully saved {created_count} phrase pairs for '{lexical_unit.lemma}'."
            )

    except json.JSONDecodeError:
        logger.error(
            f"Failed to decode JSON for '{lexical_unit.lemma}'. Response: {raw_response}"
        )
    except Exception as e:
        logger.error(
            f"General failure in parse_and_save_phrases for '{lexical_unit.lemma}': {e}",
            exc_info=True,
        )

    return created_count
