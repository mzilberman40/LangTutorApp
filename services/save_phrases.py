# In services/save_phrases.py

import json
import logging
from learning.models import Phrase, LexicalUnit, PhraseTranslation

logger = logging.getLogger(__name__)


def parse_and_save_phrases(
    raw_response: str,
    lexical_unit: LexicalUnit,
    # These are the language codes corresponding to 'lang2' and 'lang1'
    # from the unit2phrases service call.
    example_lang_code: str,  # Language of the generated example phrases (e.g., "en-GB")
    translation_lang_code: str,  # Language into which examples are translated (e.g., "ru")
):
    """
    Parses the JSON response from the LLM (expected to be a list of phrase pairs)
    and saves them as Phrase objects and PhraseTranslation links.

    Args:
        raw_response: The raw JSON string from the LLM.
        lexical_unit: The LexicalUnit for which these phrases are examples.
        example_lang_code: The BCP47 code for the language of the example sentences
                           (this was 'lang2' in the unit2phrases prompt).
        translation_lang_code: The BCP47 code for the language of the translated sentences
                               (this was 'lang1' in the unit2phrases prompt).
    Returns:
        int: Count of successfully created phrase pairs.
    """
    created_phrase_pairs_count = 0
    try:
        data = json.loads(raw_response)
        if not isinstance(data, list):
            logger.error(
                f"❌ LLM response for '{lexical_unit.lemma}' is not a list. Response: {raw_response}"
            )
            return created_phrase_pairs_count

        for item in data:
            if not isinstance(item, dict):
                logger.warning(
                    f"⚠️ Skipping non-dictionary item in LLM response for '{lexical_unit.lemma}': {item}"
                )
                continue

            example_sentence_text = item.get(example_lang_code)
            translated_sentence_text = item.get(translation_lang_code)
            cefr_level = item.get("CEFR")  # As per your unit2phrase.txt prompt

            if not all([example_sentence_text, translated_sentence_text, cefr_level]):
                logger.warning(
                    f"⚠️ Skipping phrase pair for '{lexical_unit.lemma}' due to missing data. "
                    f"Example: '{example_sentence_text}', Translation: '{translated_sentence_text}', CEFR: '{cefr_level}'"
                )
                continue

            try:
                # Create the Phrase object for the example sentence (in example_lang_code)
                phrase_example = Phrase.objects.create(
                    text=example_sentence_text,
                    language=example_lang_code,
                    cefr=cefr_level,
                    # category can be set if your LLM provides it, or use default
                )
                # Link this example phrase to the lexical unit it exemplifies
                phrase_example.units.add(lexical_unit)

                # Create the Phrase object for the translated sentence (in translation_lang_code)
                phrase_translation_of_example = Phrase.objects.create(
                    text=translated_sentence_text,
                    language=translation_lang_code,
                    cefr=cefr_level,  # Assuming CEFR applies to both, or adjust as needed
                    # category can be set similarly
                )

                # Create the PhraseTranslation link.
                # Assuming the example sentence (phrase_example) is the "source"
                # as per the prompt "Translate each {lang2} sentence into {lang1}"
                PhraseTranslation.objects.create(
                    source_phrase=phrase_example,
                    target_phrase=phrase_translation_of_example,
                )
                created_phrase_pairs_count += 1
            except Exception as e_inner:
                logger.error(
                    f"❌ Failed to save a specific phrase pair for '{lexical_unit.lemma}' "
                    f"('{example_sentence_text}' / '{translated_sentence_text}'): {e_inner}"
                )
                # Optionally, decide if you want to continue with other pairs or re-raise

        if created_phrase_pairs_count > 0:
            logger.info(
                f"✅ Successfully parsed and saved {created_phrase_pairs_count} phrase pairs "
                f"for LexicalUnit '{lexical_unit.lemma}'."
            )
        else:
            logger.warning(
                f"⚠️ No phrase pairs were saved for LexicalUnit '{lexical_unit.lemma}' from response: {raw_response}"
            )

    except json.JSONDecodeError as e:
        logger.error(
            f"❌ Failed to decode JSON response for '{lexical_unit.lemma}': {e}. Response: {raw_response}"
        )
    except Exception as e_outer:
        logger.error(
            f"❌ General failure in parse_and_save_phrases for unit '{lexical_unit.lemma}': {e_outer}"
        )

    return created_phrase_pairs_count
