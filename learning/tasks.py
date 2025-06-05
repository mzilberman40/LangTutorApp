"""
Background Celery task for generating example phrases based on a given word.
This task uses an external LLM client to generate phrases and then delegates saving to a service.
"""

import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from learning.enums import TranslationType
from learning.models import LexicalUnit, LexicalUnitTranslation
from services.unit2phrases import unit2phrases
from services.save_phrases import parse_and_save_phrases
from ai.client import get_client

logger = logging.getLogger(__name__)


@shared_task
def generate_phrases_async(
    unit_id: int,
    target_translation_lang_code: str,  # <<< It needs to expect this
    cefr_level_for_phrases: str,  # <<< And this
):
    try:
        unit = LexicalUnit.objects.get(id=unit_id)
    except ObjectDoesNotExist:
        logger.error(f"❌ LexicalUnit with id={unit_id} not found.")
        return

    example_lang_code = unit.language

    if target_translation_lang_code.lower() == example_lang_code.lower():
        logger.error(
            f"❌ Cannot generate phrases: LexicalUnit language ('{example_lang_code}') "
            f"is the same as the requested target translation language ('{target_translation_lang_code}') for unit id={unit_id}."
        )
        return

    client = get_client()

    try:
        raw_response = unit2phrases(
            client,
            unit.lemma,
            cefr=cefr_level_for_phrases,
            lang1=target_translation_lang_code,
            lang2=example_lang_code,
        )
        parse_and_save_phrases(
            raw_response,
            unit,
            example_lang_code=example_lang_code,
            translation_lang_code=target_translation_lang_code,
        )
    except Exception as e:
        logger.error(
            f"❌ Phrase generation pipeline failed for unit id={unit_id} ('{unit.lemma}'): {e}"
        )


@shared_task
def enrich_lexical_unit_async(
    unit_id: int, target_language_codes: list = None, force_update: bool = False
):
    logger.info(
        f"Starting enrichment for LexicalUnit ID: {unit_id}, Targets: {target_language_codes}, Force: {force_update}"
    )
    try:
        unit = LexicalUnit.objects.get(id=unit_id)
    except ObjectDoesNotExist:
        logger.error(f"❌ LexicalUnit with id={unit_id} not found for enrichment.")
        return

    client = get_client()  # Assuming get_client() is defined
    details_updated = False

    # Step 1: Fill details for the original unit if needed
    if force_update or not unit.part_of_speech or not unit.pronunciation:
        try:
            # prompt_template_details = PROMPT_GET_DETAILS_PATH.read_text(encoding="utf-8")
            # prompt_details = prompt_template_details.format(lemma=unit.lemma, language_code=unit.language)
            # raw_details_response = answer_with_llm(client=client, prompt=prompt_details, model="your_chosen_model") # Adjust model/params
            # details_data = json.loads(raw_details_response)

            # This is a placeholder for actual LLM call and parsing for details
            details_data = {}  # Replace with actual LLM call
            llm_pos = details_data.get("part_of_speech")
            llm_pronunciation = details_data.get("pronunciation")

            logger.info(
                f"LLM details for '{unit.lemma}': POS='{llm_pos}', Pronunciation='{llm_pronunciation}'"
            )

            if llm_pos and (force_update or not unit.part_of_speech):
                unit.part_of_speech = llm_pos
                details_updated = True
            if llm_pronunciation and (force_update or not unit.pronunciation):
                unit.pronunciation = llm_pronunciation
                details_updated = True

            if details_updated:
                unit.save()  # The save method will also handle lemma canonicalization and unit_type
                logger.info(f"Updated details for LexicalUnit ID: {unit.id}")

        except Exception as e:
            logger.error(
                f"❌ Failed to get/update details for LexicalUnit ID {unit.id}: {e}"
            )

    # Step 2: Translate if target languages are provided
    if target_language_codes:
        for target_lang in target_language_codes:
            target_lang = target_lang.strip().lower()
            if not target_lang or target_lang == unit.language.lower():
                logger.warning(
                    f"Skipping translation to '{target_lang}' for unit ID {unit.id} (same as source or empty)."
                )
                continue

            try:
                # prompt_template_translate = PROMPT_TRANSLATE_DETAILS_PATH.read_text(encoding="utf-8")
                # current_pos_for_prompt = unit.part_of_speech or "unknown" # Use known POS if available
                # prompt_translate = prompt_template_translate.format(
                #     source_lemma=unit.lemma,
                #     source_pos=current_pos_for_prompt,
                #     source_language_code=unit.language,
                #     target_language_code=target_lang
                # )
                # raw_translate_response = answer_with_llm(client=client, prompt=prompt_translate, model="your_chosen_model")
                # translation_data = json.loads(raw_translate_response)

                # This is a placeholder for actual LLM call and parsing for translation
                translation_data = {}  # Replace with actual LLM call
                translated_lemma_text = translation_data.get("translated_lemma")
                translated_pos = translation_data.get("part_of_speech")
                translated_pronunciation = translation_data.get("pronunciation")

                logger.info(
                    f"LLM translation for '{unit.lemma}' to '{target_lang}': Lemma='{translated_lemma_text}', POS='{translated_pos}', Pronunciation='{translated_pronunciation}'"
                )

                if translated_lemma_text:
                    # Canonicalize and determine unit_type for the translation
                    # The LexicalUnit.save() method handles this if we pass the raw lemma

                    # Get or create the translated LexicalUnit
                    # Note: The .save() method will handle canonicalization and unit_type based on spaces
                    translated_unit, created = LexicalUnit.objects.get_or_create(
                        lemma=translated_lemma_text,  # Raw lemma from LLM
                        language=target_lang,
                        defaults={
                            "part_of_speech": translated_pos or "",
                            "pronunciation": translated_pronunciation or "",
                            # unit_type will be set by save() based on spaces in canonicalized translated_lemma_text
                        },
                    )
                    if (
                        not created and force_update
                    ):  # If it existed and we want to force update its details
                        if translated_pos:
                            translated_unit.part_of_speech = translated_pos
                        if translated_pronunciation:
                            translated_unit.pronunciation = translated_pronunciation
                        # Ensure unit_type is also re-evaluated by save if lemma might change canonical form
                        translated_unit.save()

                        # Create the translation link
                    LexicalUnitTranslation.objects.get_or_create(
                        source_unit=unit,
                        target_unit=translated_unit,
                        defaults={
                            "translation_type": TranslationType.AI
                        },  # Assuming TranslationType enum exists
                    )
                    logger.info(
                        f"Processed translation of '{unit.lemma}' to '{target_lang}' (ID: {translated_unit.id})"
                    )
                else:
                    logger.warning(
                        f"No translated lemma received for '{unit.lemma}' to '{target_lang}'."
                    )

            except Exception as e:
                logger.error(
                    f"❌ Failed to translate LexicalUnit ID {unit.id} to {target_lang}: {e}"
                )
    logger.info(f"Enrichment task finished for LexicalUnit ID: {unit.id}")
