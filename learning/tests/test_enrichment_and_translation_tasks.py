# In learning/tests/test_enrichment_and_translation_tasks.py
import pytest
from unittest.mock import patch
from learning.models import LexicalUnit, LexicalUnitTranslation
from learning.enums import PartOfSpeech, ValidationStatus
from learning.tasks import enrich_details_async, translate_unit_async

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
        {"part_of_speech": "noun", "pronunciation": "/ˈkɒndʌkt/"},
        {"part_of_speech": "verb", "pronunciation": "/kənˈdʌkt/"},
    ]

    # Act: Запускаем задачу обогащения для существительного
    enrich_details_async(unit_id=lu_noun.id, user_id=lu_noun.user.id)

    # Assert: Проверяем, что теперь существуют ОБЕ версии
    assert LexicalUnit.objects.filter(lemma="conduct", part_of_speech="noun").exists()
    assert LexicalUnit.objects.filter(lemma="conduct", part_of_speech="verb").exists()
    # Проверяем, что общее количество записей для этого слова - 2
    assert LexicalUnit.objects.filter(lemma="conduct").count() == 2


@patch("learning.tasks.translate_lemma_with_details")
def test_translate_creates_multiple_variants_and_links(
    mock_translate, lexical_unit_factory
):
    source_lu = lexical_unit_factory(lemma="fire", language="en", part_of_speech="noun")
    mock_translate.return_value = {
        "translated_lemma": "огонь",
        "translation_details": [
            {"part_of_speech": "noun", "pronunciation": "/ɐˈɡonʲ/"},
            {"part_of_speech": "verb", "pronunciation": "/ɐˈɡonʲitʲ/"},
        ],
    }

    # FIX: Pass the user's ID to the task call.
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
def test_enrich_stops_if_initial_lu_is_mismatched(mock_get_details, lexical_unit_factory):
    """
    Тестирует, что обогащение останавливается, если исходная LU имеет
    несоответствующую часть речи (MISMATCH).
    """
    # Arrange: Создаем LU с POS='noun', но LLM вернет только 'verb'.
    lu_to_test = lexical_unit_factory(lemma="delegate", part_of_speech="noun")
    mock_get_details.return_value = [{"part_of_speech": "verb"}]

    # Act: Запускаем задачу
    enrich_details_async(unit_id=lu_to_test.id, user_id=lu_to_test.user.id)

    # Assert:
    # 1. Статус исходного объекта должен измениться на MISMATCH
    lu_to_test.refresh_from_db()
    assert lu_to_test.validation_status == ValidationStatus.MISMATCH
    assert "LLM suggested: [verb]" in lu_to_test.validation_notes

    # 2. Самое главное: новый вариант (verb) НЕ должен быть создан
    assert not LexicalUnit.objects.filter(lemma="delegate", part_of_speech="verb").exists()


@patch("learning.tasks.get_lemma_details")
def test_enrich_stops_if_initial_lu_is_not_found_by_llm(mock_get_details, lexical_unit_factory):
    """
    Тестирует, что обогащение останавливается, если LLM не находит
    никаких вариантов для леммы (FAILED).
    """
    # Arrange: Создаем LU с "фальшивой" леммой, и LLM возвращает пустой список
    lu_to_test = lexical_unit_factory(lemma="asdfqwerty", part_of_speech="noun")
    mock_get_details.return_value = []

    # Act: Запускаем задачу
    enrich_details_async(unit_id=lu_to_test.id, user_id=lu_to_test.user.id)

    # Assert:
    # 1. Статус исходного объекта должен измениться на FAILED
    lu_to_test.refresh_from_db()
    assert lu_to_test.validation_status == ValidationStatus.FAILED
    assert "LLM could not find any valid forms" in lu_to_test.validation_notes

    # 2. Никаких новых объектов не создано (просто для уверенности)
    assert LexicalUnit.objects.filter(lemma="asdfqwerty").count() == 1
