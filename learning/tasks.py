"""
Background Celery task for generating example phrases based on a given word.
This task uses an external LLM client to generate phrases and then delegates saving to a service.
"""

import json
import logging

# from pathlib import Path

from celery import shared_task
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from ai.answer_with_llm import answer_with_llm
from learning.enums import TranslationType, PartOfSpeech
from learning.models import LexicalUnit, LexicalUnitTranslation
from services.get_lemma_details import get_lemma_details
from services.translate_lemma import translate_lemma_with_details
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


#
# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def enrich_details_async(self, unit_id: int, force_update: bool = False):
#     logger.info(
#         f"Starting detail enrichment for LexicalUnit ID: {unit_id}, Force: {force_update}"
#     )
#     try:
#         initial_lu = LexicalUnit.objects.get(id=unit_id)
#     except ObjectDoesNotExist:
#         logger.error(f"❌ LexicalUnit with id={unit_id} not found for enrichment.")
#         return f"LexicalUnit ID {unit_id} not found."
#
#     # This enrichment logic should only run if the POS is not already specified, or if forced.
#     if not force_update and initial_lu.part_of_speech:
#         logger.info(
#             f"LexicalUnit {unit_id} already has a specific Part of Speech. Skipping detail enrichment (use force_update=True to override)."
#         )
#         return f"Enrichment skipped for LU {unit_id}."
#
#     try:
#         logger.info(
#             f"Resolving/Updating POS details for {initial_lu.lemma} ({initial_lu.language})..."
#         )
#         client = get_client()
#         lemma_details_list = get_lemma_details(client, initial_lu)
#
#         if not lemma_details_list:
#             logger.warning(
#                 f"No POS details were returned from LLM for '{initial_lu.lemma}'."
#             )
#             return "No POS details found from LLM."
#
#         # --- Corrected if/else Structure ---
#         if len(lemma_details_list) == 1:
#             # CASE 1: LLM found exactly one POS variant. Update the original LU in-place.
#             logger.info(
#                 f"LLM found a single POS variant for '{initial_lu.lemma}'. Updating original LU (ID: {initial_lu.id})."
#             )
#             detail = lemma_details_list[0]
#             pos = detail.get("part_of_speech")
#             pron = detail.get("pronunciation")
#
#             if pos and pos in PartOfSpeech.values:
#                 # Check if updating this LU would cause a unique constraint violation
#                 if (
#                     LexicalUnit.objects.filter(
#                         lemma=initial_lu.lemma,
#                         language=initial_lu.language,
#                         part_of_speech=pos,
#                     )
#                     .exclude(pk=initial_lu.pk)
#                     .exists()
#                 ):
#                     logger.warning(
#                         f"Could not update LU {initial_lu.id} with POS '{pos}' because a specific variant already exists."
#                     )
#                 else:
#                     initial_lu.part_of_speech = pos
#                     initial_lu.pronunciation = pron or ""
#                     initial_lu.save()  # Save the changes to the original LU
#                     logger.info(
#                         f"Successfully updated original LU {initial_lu.id} with details: {detail}"
#                     )
#             else:
#                 logger.warning(
#                     f"LLM returned an invalid POS ('{pos}'). Original LU not updated."
#                 )
#
#         else:  # Case for len(lemma_details_list) > 1
#             # CASE 2: LLM found multiple POS variants. Create/update new LUs for each.
#             logger.info(
#                 f"LLM found multiple ({len(lemma_details_list)}) variants for '{initial_lu.lemma}'. Creating/updating specific entries."
#             )
#             created_or_found_specific_variants = []
#             for detail in lemma_details_list:
#                 pos = detail.get("part_of_speech")
#                 pron = detail.get("pronunciation")
#                 if pos and pos in PartOfSpeech.values:
#                     specific_variant, created = LexicalUnit.objects.get_or_create(
#                         lemma=initial_lu.lemma,
#                         language=initial_lu.language,
#                         part_of_speech=pos,
#                         defaults={"pronunciation": pron or ""},
#                     )
#                     created_or_found_specific_variants.append(specific_variant)
#                     logger.info(
#                         f"{'Created' if created else 'Found'} specific variant: {specific_variant}"
#                     )
#                     if (
#                         not created
#                         and force_update
#                         and pron
#                         and specific_variant.pronunciation != pron
#                     ):
#                         specific_variant.pronunciation = pron
#                         specific_variant.save()
#                 else:
#                     logger.warning(
#                         f"LLM returned invalid POS ('{pos}'). Skipping this variant."
#                     )
#
#             # Deletion logic now correctly nested inside the 'else' block
#             if initial_lu.part_of_speech == "" and created_or_found_specific_variants:
#                 # Safety check before deleting the original, underspecified LU
#                 has_translations = (
#                     initial_lu.translations_from.exists()
#                     or initial_lu.translations_to.exists()
#                 )
#                 has_phrase_links = initial_lu.phrase_set.exists()
#                 if not has_translations and not has_phrase_links:
#                     logger.info(
#                         f"Deleting redundant, unspecified LU (ID: {initial_lu.id}) as it has been replaced and has no relations."
#                     )
#                     initial_lu.delete()
#                 else:
#                     logger.warning(
#                         f"Redundant LU (ID: {initial_lu.id}) was NOT deleted because it has existing relationships."
#                     )
#
#     except Exception as e_detail:
#         logger.error(
#             f"An error occurred during detail enrichment for '{initial_lu.lemma}': {e_detail}"
#         )
#         self.retry(exc=e_detail)  # Retry on unexpected errors
#
#     return f"Enrichment process completed for original unit {unit_id}."


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_details_async(self, unit_id: int, user_id: int, force_update: bool = False):
    logger.info(
        f"Starting detail enrichment for LU ID: {unit_id} for User ID: {user_id}"
    )
    try:
        # Fetch the user who initiated the task
        user = User.objects.get(pk=user_id)
        initial_lu = LexicalUnit.objects.get(
            id=unit_id, user=user
        )  # Also scope this lookup
    except ObjectDoesNotExist:
        logger.error(f"❌ LexicalUnit with id={unit_id} not found for enrichment.")
        return f"LexicalUnit ID {unit_id} not found."

    # We only proceed if the LU is underspecified (no POS) or if a force_update is requested.
    if not force_update and initial_lu.part_of_speech:
        logger.info(
            f"LexicalUnit {unit_id} already has a specific Part of Speech. Skipping detail enrichment."
        )
        return f"Enrichment skipped for LU {unit_id}."

    try:
        logger.info(
            f"Resolving/Updating POS details for '{initial_lu.lemma}' ({initial_lu.language})..."
        )
        client = get_client()
        lemma_details_list = get_lemma_details(client, initial_lu)

        if not lemma_details_list:
            logger.warning(
                f"No POS details were returned from LLM for '{initial_lu.lemma}'."
            )
            return "No POS details found from LLM."

        # Always use the get_or_create loop for all variants returned by the LLM
        created_or_found_specific_variants = []
        for detail in lemma_details_list:
            pos = detail.get("part_of_speech")
            pron = detail.get("pronunciation")

            if pos and pos in PartOfSpeech.values:
                specific_variant, created = LexicalUnit.objects.get_or_create(
                    lemma=initial_lu.lemma,
                    user=user,
                    language=initial_lu.language,
                    part_of_speech=pos,
                    defaults={"pronunciation": pron or ""},
                )
                created_or_found_specific_variants.append(specific_variant)
                logger.info(
                    f"{'Created' if created else 'Found'} specific variant: {specific_variant}"
                )

                if (
                    not created
                    and force_update
                    and pron
                    and specific_variant.pronunciation != pron
                ):
                    specific_variant.pronunciation = pron
                    specific_variant.save()
            else:
                logger.warning(
                    f"LLM returned invalid POS ('{pos}') for '{initial_lu.lemma}'. Skipping this variant."
                )

        # --- 👇 NEW AND CRUCIAL: Deletion Logic for the Original Stub ---
        # If the original LU was underspecified (had an empty POS) AND
        # we successfully created/found at least one specific variant for it...
        if initial_lu.part_of_speech == "" and created_or_found_specific_variants:
            # We must ensure the original LU isn't linked to anything else before deleting.
            has_translations = (
                initial_lu.translations_from.exists()
                or initial_lu.translations_to.exists()
            )
            has_phrase_links = initial_lu.phrase_set.exists()

            if not has_translations and not has_phrase_links:
                logger.info(
                    f"Deleting redundant, unspecified LU (ID: {initial_lu.id}) as it has been replaced and has no relations."
                )
                initial_lu.delete()
            else:
                logger.warning(
                    f"Redundant, unspecified LU (ID: {initial_lu.id}) was NOT deleted because it is linked in translations or phrases. "
                    "These relationships may need to be migrated manually."
                )

    except Exception as e:
        logger.error(
            f"An error occurred during detail enrichment for '{initial_lu.lemma}': {e}"
        )
        self.retry(exc=e)

    return f"Enrichment process completed for original unit {unit_id}."


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def translate_unit_async(self, unit_id: int, user_id: int, target_language_code: str):
    """
    Translates a single, specific LexicalUnit into a target language,
    creating new specific variant(s) for the translation for the correct user.
    """
    logger.info(
        f"Starting translation for LU ID {unit_id} (User ID: {user_id}) to '{target_language_code}'..."
    )
    try:
        # Fetch both the source LU and the user who owns it
        user = User.objects.get(pk=user_id)
        source_lu = LexicalUnit.objects.get(id=unit_id, user=user)
    except ObjectDoesNotExist:
        logger.error(f"❌ Source LU with id={unit_id} for user={user_id} not found.")
        return

    client = get_client()
    try:
        translation_response = translate_lemma_with_details(
            client, source_lu, target_language_code
        )

        translated_base_lemma = translation_response.get("translated_lemma")
        details_for_translation = translation_response.get("translation_details", [])

        if not translated_base_lemma or not details_for_translation:
            logger.warning(
                f"Insufficient data from LLM for translation of '{source_lu.lemma}'"
            )
            return

        for trans_detail in details_for_translation:
            trans_pos = trans_detail.get("part_of_speech")
            trans_pron = trans_detail.get("pronunciation")

            if not (trans_pos and trans_pos in PartOfSpeech.values):
                logger.warning(f"Skipping variant due to invalid POS '{trans_pos}'")
                continue

            # --- THE FIX IS HERE ---
            # When creating the new translated LU, assign it to the SAME USER.
            final_translated_lu, _ = LexicalUnit.objects.get_or_create(
                user=user,  # <-- THIS LINE FIXES THE BUG
                lemma=translated_base_lemma,
                language=target_language_code,
                part_of_speech=trans_pos,
                defaults={"pronunciation": trans_pron or ""},
            )

            LexicalUnitTranslation.objects.get_or_create(
                source_unit=source_lu,
                target_unit=final_translated_lu,
                defaults={"translation_type": TranslationType.AI},
            )
            logger.info(f"Successfully linked {source_lu} -> {final_translated_lu}")

    except Exception as e_trans:
        logger.error(f"❌ Error in translation pipeline for {source_lu}: {e_trans}")
        self.retry(exc=e_trans)


@shared_task(bind=True)
def resolve_lemma_async(self, lemma: str, language: str, user_id: int):
    """
    Asynchronously resolves a lemma, finds its variants, checks which ones
    already exist for the user, and returns the list of processed variants.
    """
    try:
        user = User.objects.get(pk=user_id)
        client = get_client()

        # This logic is moved from the view into the task
        temp_lu = LexicalUnit(lemma=lemma, language=language)
        llm_variants = get_lemma_details(client, temp_lu)

        if not llm_variants:
            # If no variants are found, the task result will be an empty list
            return []

        existing_pos_for_user = set(
            LexicalUnit.objects.filter(
                user=user, lemma=lemma, language=language
            ).values_list("part_of_speech", flat=True)
        )

        processed_variants = []
        for variant in llm_variants:
            variant["exists"] = variant.get("part_of_speech") in existing_pos_for_user
            processed_variants.append(variant)

        # The return value of the task is automatically stored in the Celery result backend.
        return processed_variants
    except Exception as e:
        logger.error(f"Error in resolve_lemma_async for lemma '{lemma}': {e}")
        # If an error occurs, Celery will store the exception.
        raise
