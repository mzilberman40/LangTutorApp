# learning/tasks.py
import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from learning.enums import TranslationType, PartOfSpeech, ValidationStatus
from learning.models import LexicalUnit, LexicalUnitTranslation, Phrase
from services.enrich_phrase_details import enrich_phrase_details
from services.extract_lemmas import extract_lemmas_from_text
from services.get_lemma_details import get_lemma_details
from services.translate_lemma import translate_lemma_with_details
from services.unit2phrases import unit2phrases
from services.save_phrases import parse_and_save_phrases
from ai.client import get_client
from services.verify_translation import get_translation_verification

logger = logging.getLogger(__name__)


@shared_task
def generate_phrases_async(unit_id: int, target_language: str, cefr_level: str):
    try:
        unit = LexicalUnit.objects.get(id=unit_id)
    except ObjectDoesNotExist:
        logger.error(f"❌ LexicalUnit with id={unit_id} not found.")
        return

    source_language = unit.language

    if target_language.lower() == source_language.lower():
        logger.error(
            f"❌ Source and target languages are the same ('{source_language}')."
        )
        return

    client = get_client()
    try:
        raw_response = unit2phrases(
            client=client,
            lemma=unit.lemma,
            cefr=cefr_level,
            source_language=source_language,
            target_language=target_language,
        )
        parse_and_save_phrases(
            raw_response=raw_response,
            lexical_unit=unit,
            source_language=source_language,
            target_language=target_language,
        )
    except Exception as e:
        logger.error(
            f"❌ Phrase generation pipeline failed for unit id={unit_id}: {e}",
            exc_info=True,
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_details_async(self, unit_id: int, user_id: int, force_update: bool = False):
    logger.info(f"Starting enrichment process for LU ID: {unit_id}")
    try:
        user = User.objects.get(pk=user_id)
        initial_lu = LexicalUnit.objects.get(id=unit_id, user=user)
    except ObjectDoesNotExist:
        logger.error(f"Cannot enrich: LU with id={unit_id} not found.")
        return

    try:
        client = get_client()
        all_variants = get_lemma_details(client, initial_lu)

        if not all_variants:
            initial_lu.validation_status = ValidationStatus.FAILED
            initial_lu.validation_notes = (
                "LLM could not find any valid forms for this lemma."
            )
            initial_lu.save(update_fields=["validation_status", "validation_notes"])
            logger.warning(f"Enrichment stopped: Initial LU {unit_id} is not valid.")
            return

        is_initial_lu_valid = any(
            v.get("part_of_speech") == initial_lu.part_of_speech for v in all_variants
        )

        if not is_initial_lu_valid:
            initial_lu.validation_status = ValidationStatus.MISMATCH
            suggested_pos = ", ".join(
                [v.get("part_of_speech", "N/A") for v in all_variants]
            )
            initial_lu.validation_notes = f"Saved POS '{initial_lu.part_of_speech}' is not a likely variant. LLM suggested: [{suggested_pos}]."
            initial_lu.save(update_fields=["validation_status", "validation_notes"])
            logger.warning(
                f"Enrichment stopped: Initial LU {unit_id} has a mismatched POS."
            )
            return
        else:
            if initial_lu.validation_status != ValidationStatus.VALID:
                initial_lu.validation_status = ValidationStatus.VALID
                initial_lu.validation_notes = "Verified during enrichment process."
                initial_lu.save(update_fields=["validation_status", "validation_notes"])

        logger.info(
            f"Initial LU {unit_id} is valid. Proceeding to enrich with other POS variants."
        )
        for detail in all_variants:
            if detail.get("part_of_speech") == initial_lu.part_of_speech:
                continue

            specific_variant, created = LexicalUnit.objects.get_or_create(
                lemma=initial_lu.lemma,
                user=user,
                language=initial_lu.language,
                part_of_speech=detail.get("part_of_speech"),
                defaults={"pronunciation": detail.get("pronunciation") or ""},
            )
            if created:
                logger.info(
                    f"Created new specific variant during enrichment: {specific_variant}"
                )

    except Exception as e:
        logger.error(
            f"An error occurred during enrichment for LU {unit_id}: {e}", exc_info=True
        )
        self.retry(exc=e)
    return f"Enrichment process completed for original unit {unit_id}."


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def translate_unit_async(self, unit_id: int, user_id: int, target_language_code: str):
    logger.info(
        f"Starting translation for LU ID {unit_id} to '{target_language_code}'..."
    )
    try:
        user = User.objects.get(pk=user_id)
        source_lu = LexicalUnit.objects.get(id=unit_id, user=user)
    except ObjectDoesNotExist:
        logger.error(f"❌ Source LU with id={unit_id} for user={user_id} not found.")
        return

    try:
        client = get_client()
        translation_response = translate_lemma_with_details(
            client, source_lu, target_language_code
        )

        if translation_response is None:
            logger.error(
                f"Did not receive a valid translation object for '{source_lu.lemma}'. Aborting task."
            )
            return

        translated_base_lemma = translation_response.translated_lemma
        details_for_translation = translation_response.translation_details

        if not translated_base_lemma or not details_for_translation:
            logger.warning(
                f"Insufficient data from LLM for translation of '{source_lu.lemma}'"
            )
            return

        for trans_detail in details_for_translation:
            trans_pos = trans_detail.part_of_speech
            trans_pron = trans_detail.pronunciation

            if not (trans_pos and trans_pos in PartOfSpeech.values):
                logger.warning(f"Skipping variant due to invalid POS '{trans_pos}'")
                continue

            final_translated_lu, _ = LexicalUnit.objects.get_or_create(
                user=user,
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
    try:
        user = User.objects.get(pk=user_id)
        client = get_client()
        temp_lu = LexicalUnit(lemma=lemma, language=language)
        llm_variants = get_lemma_details(client, temp_lu)
        if not llm_variants:
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
        return processed_variants
    except Exception as e:
        logger.error(f"Error in resolve_lemma_async for lemma '{lemma}': {e}")
        raise


@shared_task(bind=True)
def verify_translation_link_async(self, translation_id: int):
    logger.info(f"Starting translation link verification for ID: {translation_id}")
    try:
        translation = LexicalUnitTranslation.objects.select_related(
            "source_unit", "target_unit"
        ).get(id=translation_id)
    except ObjectDoesNotExist:
        logger.error(
            f"Cannot verify: Translation link with id={translation_id} not found."
        )
        return
    try:
        client = get_client()
        response_data = get_translation_verification(
            client, translation.source_unit, translation.target_unit
        )
        if response_data is None:
            raise ValueError("Verification service did not return a valid response.")
        score = response_data.quality_score
        justification = response_data.justification
        translation.confidence = score / 5.0
        if score >= 4:
            translation.validation_status = ValidationStatus.VALID
        elif score >= 2:
            translation.validation_status = ValidationStatus.MISMATCH
        else:
            translation.validation_status = ValidationStatus.FAILED
        translation.validation_notes = justification
    except Exception as e:
        logger.error(
            f"Error during translation link verification for ID {translation.id}: {e}",
            exc_info=True,
        )
        translation.validation_status = ValidationStatus.FAILED
        translation.validation_notes = f"Verification process failed: {str(e)}"
        translation.confidence = 0.0
    finally:
        translation.save(
            update_fields=["validation_status", "validation_notes", "confidence"]
        )
        logger.info(
            f"Verification for link {translation.id} finished with status '{translation.validation_status}' and confidence {translation.confidence}."
        )


@shared_task(bind=True, max_retries=2)
def validate_lu_integrity_async(self, unit_id: int):
    logger.info(f"Starting integrity validation for LU ID: {unit_id}")
    try:
        unit = LexicalUnit.objects.get(id=unit_id)
    except ObjectDoesNotExist:
        logger.error(f"Cannot validate: LexicalUnit with id={unit_id} not found.")
        return
    try:
        client = get_client()
        llm_variants = get_lemma_details(client, unit)
        if not llm_variants:
            unit.validation_status = ValidationStatus.FAILED
            unit.validation_notes = (
                "LLM did not return any valid variants for this lemma."
            )
            unit.save(update_fields=["validation_status", "validation_notes"])
            logger.warning(f"Validation failed for LU {unit.id}: No variants from LLM.")
            return
        found_match = False
        for variant in llm_variants:
            if variant.get("part_of_speech") == unit.part_of_speech:
                unit.validation_status = ValidationStatus.VALID
                unit.validation_notes = ""
                found_match = True
                break
        if not found_match:
            unit.validation_status = ValidationStatus.MISMATCH
            suggested_pos = ", ".join(
                [v.get("part_of_speech", "N/A") for v in llm_variants]
            )
            unit.validation_notes = f"Saved POS is '{unit.part_of_speech}', but LLM suggested: [{suggested_pos}]."
            logger.warning(
                f"Validation mismatch for LU {unit.id}: {unit.validation_notes}"
            )
        unit.save(update_fields=["validation_status", "validation_notes"])
    except Exception as e:
        logger.error(f"Error during validation for LU {unit.id}: {e}")
        self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def enrich_phrase_async(self, phrase_id: int):
    """
    Asynchronously enriches a Phrase object by verifying it and filling in
    missing details using an LLM. Now with robust error handling.
    """
    logger.info(f"Starting enrichment task for Phrase ID: {phrase_id}")
    try:
        phrase = Phrase.objects.get(id=phrase_id)
    except ObjectDoesNotExist:
        logger.error(f"Cannot enrich: Phrase with id={phrase_id} not found.")
        return

    try:
        client = get_client()
        analysis = enrich_phrase_details(client, phrase)

        # --- REFACTORED LOGIC TO HANDLE SERVICE FAILURE ---
        if not analysis:
            # This is a permanent failure (bad LLM response).
            # Mark the phrase as failed and exit gracefully without retrying.
            phrase.validation_status = ValidationStatus.FAILED
            phrase.validation_notes = "Enrichment failed: the analysis service did not return a valid response from the LLM."
            phrase.save()
            logger.warning(
                f"Enrichment for Phrase {phrase_id} marked as FAILED due to service error."
            )
            return

        is_mismatch = False
        notes = []

        if not analysis.is_valid:
            is_mismatch = True
            if analysis.justification:
                notes.append(analysis.justification)
        else:
            if analysis.justification:
                notes.append(analysis.justification)

        db_lang_base = phrase.language.lower().split("-")[0]
        llm_lang_base = analysis.language_code.lower().split("-")[0]
        if db_lang_base != llm_lang_base:
            is_mismatch = True
            notes.insert(
                0,
                f"Language mismatch: saved as '{phrase.language}', but detected as '{analysis.language_code}'.",
            )

        if phrase.cefr and phrase.cefr != analysis.cefr_level:
            is_mismatch = True
            notes.append(
                f"CEFR level mismatch: saved as '{phrase.cefr}', but estimated as '{analysis.cefr_level}'."
            )

        if phrase.category and phrase.category != analysis.category:
            is_mismatch = True
            notes.append(
                f"Category mismatch: saved as '{phrase.category}', but estimated as '{analysis.category}'."
            )

        phrase.validation_status = (
            ValidationStatus.MISMATCH if is_mismatch else ValidationStatus.VALID
        )

        if not phrase.cefr:
            phrase.cefr = analysis.cefr_level
        if not phrase.category:
            phrase.category = analysis.category

        phrase.validation_notes = " | ".join(notes)
        phrase.save()
        logger.info(
            f"Enrichment for Phrase {phrase_id} finished with status '{phrase.validation_status}'."
        )
        # --- END OF REFACTORED LOGIC ---

    except Exception as e:
        # This block will now only catch truly unexpected errors.
        logger.error(
            f"An unexpected error occurred during phrase enrichment for ID {phrase_id}: {e}",
            exc_info=True,
        )
        phrase.validation_status = ValidationStatus.FAILED
        phrase.validation_notes = f"Enrichment process failed: {str(e)}"
        phrase.save()
        self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_text_and_suggest_words_async(self, text: str, user_id: int):
    """
    Asynchronously analyzes a text block, identifies new lemmas, and suggests words
    to the user based on their existing dictionary. CEFR filtering is now done manually by the user.

    Args:
        text: The text block to analyze.
        user_id: The ID of the user.

    Returns:
        A list of suggested lemmas (strings) or an error message.
    """
    logger.info(f"Starting text analysis for user {user_id}.")
    suggested_lemmas = []
    try:
        user = User.objects.get(pk=user_id)
        client = get_client()

        # Step 1: Extract lemmas from the text using the dedicated service
        extracted_lemmas = extract_lemmas_from_text(
            client, text
        )  # ИСПОЛЬЗУЕМ НОВЫЙ СЕРВИС

        if not extracted_lemmas:
            logger.warning(
                f"No lemmas found or text analysis failed for user {user_id}."
            )
            return {
                "status": "failed",
                "message": "Could not extract lemmas from the text.",
            }

        # Step 2: Get all lemmas already known by the user, case-insensitively
        user_known_lemmas = set(
            LexicalUnit.objects.filter(user=user)
            .values_list("lemma", flat=True)
            .distinct()
        )
        # Convert known lemmas to lowercase for case-insensitive comparison
        user_known_lemmas_lower = {lemma.lower() for lemma in user_known_lemmas}

        # Step 3: Filter out known lemmas.
        for lemma in extracted_lemmas:
            lemma_lower = lemma.lower()
            if lemma_lower not in user_known_lemmas_lower:
                suggested_lemmas.append(lemma)

        return {
            "status": "success",
            "suggested_words": sorted(list(set(suggested_lemmas))),
        }
    except ObjectDoesNotExist:
        logger.error(f"User with id={user_id} not found.")
        self.retry(exc=ObjectDoesNotExist())
    except Exception as e:
        logger.error(
            f"Error in analyze_text_and_suggest_words_async for user {user_id}: {e}",
            exc_info=True,
        )
        self.retry(exc=e)
