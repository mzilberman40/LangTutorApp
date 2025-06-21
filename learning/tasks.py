"""
Background Celery task for generating example phrases based on a given word.
This task uses an external LLM client to generate phrases and then delegates saving to a service.
"""

import logging
from celery import shared_task
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from learning.enums import TranslationType, PartOfSpeech, ValidationStatus
from learning.models import LexicalUnit, LexicalUnitTranslation, Phrase
from services.enrich_phrase_details import enrich_phrase_details
from services.get_lemma_details import get_lemma_details
from services.translate_lemma import translate_lemma_with_details
from services.unit2phrases import unit2phrases
from services.save_phrases import parse_and_save_phrases
from ai.client import get_client
from services.verify_translation import get_translation_verification

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_details_async(self, unit_id: int, user_id: int, force_update: bool = False):
    """
    Validates the initial LU first. If it's valid, proceeds to find and
    create all other possible parts of speech for its lemma.
    """
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

        # --- ШАГ 1: ВАЛИДАЦИЯ ИСХОДНОГО ОБЪЕКТА ---
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
            return  # Останавливаем процесс, если исходный объект некорректен
        else:
            # Если исходный объект корректен, помечаем его как валидный
            if initial_lu.validation_status != ValidationStatus.VALID:
                initial_lu.validation_status = ValidationStatus.VALID
                initial_lu.validation_notes = "Verified during enrichment process."
                initial_lu.save(update_fields=["validation_status", "validation_notes"])

        # --- ШАГ 2: ОБОГАЩЕНИЕ (выполняется, только если исходный LU валиден) ---
        logger.info(
            f"Initial LU {unit_id} is valid. Proceeding to enrich with other POS variants."
        )
        for detail in all_variants:
            # Пропускаем вариант, который уже является нашим исходным объектом
            if detail.get("part_of_speech") == initial_lu.part_of_speech:
                continue

            # Создаем только недостающие варианты
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


@shared_task(bind=True)
def verify_translation_link_async(self, translation_id: int):
    """
    Asynchronously verifies the quality of a translation link by calling
    the verification service.
    """
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

        # Рассчитываем confidence
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
        # Устанавливаем confidence в 0 при ошибке
        translation.confidence = 0.0

    finally:
        # 👇👇👇 ИСПРАВЛЕНИЕ ЗДЕСЬ 👇👇👇
        # Добавляем 'confidence' в список обновляемых полей
        translation.save(
            update_fields=["validation_status", "validation_notes", "confidence"]
        )
        logger.info(
            f"Verification for link {translation.id} finished with status '{translation.validation_status}' and confidence {translation.confidence}."
        )


@shared_task(bind=True, max_retries=2)
def validate_lu_integrity_async(self, unit_id: int):
    """
    Asynchronously validates a LexicalUnit against an LLM to check for correctness.
    """
    logger.info(f"Starting integrity validation for LU ID: {unit_id}")
    try:
        unit = LexicalUnit.objects.get(id=unit_id)
    except ObjectDoesNotExist:
        logger.error(f"Cannot validate: LexicalUnit with id={unit_id} not found.")
        return

    try:
        client = get_client()
        # Используем существующий сервис для получения эталонных данных от LLM
        llm_variants = get_lemma_details(client, unit)

        if not llm_variants:
            unit.validation_status = ValidationStatus.FAILED
            unit.validation_notes = (
                "LLM did not return any valid variants for this lemma."
            )
            unit.save(update_fields=["validation_status", "validation_notes"])
            logger.warning(f"Validation failed for LU {unit.id}: No variants from LLM.")
            return

        # Ищем вариант, который совпадает с частью речи в нашей записи
        found_match = False
        for variant in llm_variants:
            if variant.get("part_of_speech") == unit.part_of_speech:
                unit.validation_status = ValidationStatus.VALID
                unit.validation_notes = ""  # Очищаем заметки, если все хорошо
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
    missing details using an LLM.
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

        if not analysis:
            raise ValueError("Analysis service did not return a valid response.")

        # --- Применяем логику на основе ответа LLM ---
        notes = []

        # 1. Проверка корректности и естественности
        if not analysis.is_valid:
            phrase.validation_status = ValidationStatus.MISMATCH
            if analysis.justification:
                notes.append(analysis.justification)
        else:
            phrase.validation_status = ValidationStatus.VALID
            # Если есть какая-то полезная заметка (например, о диалекте)
            if analysis.justification:
                notes.append(analysis.justification)

        # 2. Проверка языка (сравниваем с тем, что в БД)
        # Приводим к нижнему регистру для надежного сравнения
        db_lang = phrase.language.lower()
        llm_lang = analysis.language_code.lower()

        if db_lang != llm_lang:
            # Если не совпадает даже базовый язык (en vs es)
            if db_lang.split('-')[0] != llm_lang.split('-')[0]:
                phrase.validation_status = ValidationStatus.MISMATCH
                # Добавляем заметку о несоответствии языка в начало списка
                notes.insert(0, f"Language mismatch: saved as '{phrase.language}', but detected as '{analysis.language_code}'.")
            # Если это просто уточнение диалекта, заметка уже должна быть добавлена из `justification`
            # и статус уже VALID (если нет других проблем)

        # 3. Заполнение или проверка CEFR и Category
        if not phrase.cefr:
            phrase.cefr = analysis.cefr_level
        elif phrase.cefr != analysis.cefr_level:
            notes.append(f"CEFR level mismatch: saved as '{phrase.cefr}', but estimated as '{analysis.cefr_level}'.")
            phrase.validation_status = ValidationStatus.MISMATCH

        if not phrase.category:
            phrase.category = analysis.category
        elif phrase.category != analysis.category:
            notes.append(f"Category mismatch: saved as '{phrase.category}', but estimated as '{analysis.category}'.")
            phrase.validation_status = ValidationStatus.MISMATCH

        # Сохраняем все собранные заметки
        phrase.validation_notes = " | ".join(notes)

    except Exception as e:
        logger.error(f"Error during phrase enrichment for ID {phrase_id}: {e}", exc_info=True)
        phrase.validation_status = ValidationStatus.FAILED
        phrase.validation_notes = f"Enrichment process failed: {str(e)}"
        self.retry(exc=e)

    finally:
        phrase.save()
        logger.info(f"Enrichment for Phrase {phrase_id} finished with status '{phrase.validation_status}'.")
