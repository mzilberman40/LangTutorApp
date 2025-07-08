# In learning/tests/test_enrichment_and_translation_tasks.py
import pytest
from unittest.mock import patch
from learning.models import LexicalUnit, LexicalUnitTranslation
from learning.enums import PartOfSpeech, ValidationStatus, LexicalCategory
from learning.tasks import enrich_details_async, translate_unit_async
from services.translate_lemma import TranslationResponse, TranslationDetail

pytestmark = pytest.mark.django_db


@patch("learning.tasks.get_lemma_details")
def test_enrich_adds_new_pos_variant_for_existing_lu(
    mock_get_details, lexical_unit_factory
):
    """
    Тестирует, что enrich-details добавляет новый вариант (verb),
    когда уже существует другой вариант (noun).
    """
    # Arrange: Создаем исходную LU
    lu_noun = lexical_unit_factory(lemma="conduct", part_of_speech="noun")

    # LLM возвращает два варианта: существующий и новый
    mock_get_details.return_value = [
        {
            "lexical_category": "SINGLE_WORD",
            "part_of_speech": "noun",
            "pronunciation": "/ˈkɒndʌkt/",
        },
        {
            "lexical_category": "SINGLE_WORD",
            "part_of_speech": "verb",
            "pronunciation": "/kənˈdʌkt/",
        },
    ]

    # Act: Запускаем задачу обогащения для существительного
    enrich_details_async(unit_id=lu_noun.id, user_id=lu_noun.user.id)

    # Assert: Проверяем, что теперь существуют ОБЕ версии
    assert LexicalUnit.objects.filter(lemma="conduct", part_of_speech="noun").exists()
    assert LexicalUnit.objects.filter(lemma="conduct", part_of_speech="verb").exists()
    assert LexicalUnit.objects.filter(lemma="conduct").count() == 2


@patch("learning.tasks.translate_lemma_with_details")
def test_translate_creates_multiple_variants_and_links(
    mock_translate, lexical_unit_factory
):
    source_lu = lexical_unit_factory(lemma="fire", language="en", part_of_speech="noun")

    # --- FIX IS HERE ---
    # The mock must return an instance of the Pydantic model, not a raw dict,
    # because the task code expects an object with attributes.
    mock_translate.return_value = TranslationResponse(
        translated_lemma="огонь",
        translation_details=[
            TranslationDetail(
                lexical_category=LexicalCategory.SINGLE_WORD,
                part_of_speech=PartOfSpeech.NOUN,
                pronunciation="/ɐˈɡonʲ/",
            ),
            TranslationDetail(
                lexical_category=LexicalCategory.SINGLE_WORD,
                part_of_speech=PartOfSpeech.VERB,
                pronunciation="/ɐˈɡonʲitʲ/",
            ),
        ],
    )
    # --- END FIX ---

    translate_unit_async(
        unit_id=source_lu.id, user_id=source_lu.user.id, target_language_code="ru"
    )

    noun_translation = LexicalUnit.objects.get(
        user=source_lu.user, lemma="огонь", part_of_speech="noun"
    )
    verb_translation = LexicalUnit.objects.get(
        user=source_lu.user, lemma="огонь", part_of_speech="verb"
    )
    assert LexicalUnitTranslation.objects.filter(
        source_unit=source_lu, target_unit=noun_translation
    ).exists()
    assert LexicalUnitTranslation.objects.filter(
        source_unit=source_lu, target_unit=verb_translation
    ).exists()


@patch("learning.tasks.get_lemma_details")
def test_enrich_stops_if_initial_lu_is_mismatched(
    mock_get_details, lexical_unit_factory
):
    """
    Тестирует, что обогащение останавливается, если исходная LU имеет
    несоответствующую часть речи (MISMATCH).
    """
    lu_to_test = lexical_unit_factory(lemma="delegate", part_of_speech="noun")
    mock_get_details.return_value = [
        {"lexical_category": "SINGLE_WORD", "part_of_speech": "verb"}
    ]

    enrich_details_async(unit_id=lu_to_test.id, user_id=lu_to_test.user.id)

    lu_to_test.refresh_from_db()
    assert lu_to_test.validation_status == ValidationStatus.MISMATCH
    assert "LLM suggested: [verb]" in lu_to_test.validation_notes
    assert not LexicalUnit.objects.filter(
        lemma="delegate", part_of_speech="verb"
    ).exists()


@patch("learning.tasks.get_lemma_details")
def test_enrich_stops_if_initial_lu_is_not_found_by_llm(
    mock_get_details, lexical_unit_factory
):
    """
    Тестирует, что обогащение останавливается, если LLM не находит
    никаких вариантов для леммы (FAILED).
    """
    lu_to_test = lexical_unit_factory(lemma="asdfqwerty", part_of_speech="noun")
    mock_get_details.return_value = []

    enrich_details_async(unit_id=lu_to_test.id, user_id=lu_to_test.user.id)

    lu_to_test.refresh_from_db()
    assert lu_to_test.validation_status == ValidationStatus.FAILED
    assert "LLM could not find any valid forms" in lu_to_test.validation_notes
    assert LexicalUnit.objects.filter(lemma="asdfqwerty").count() == 1
