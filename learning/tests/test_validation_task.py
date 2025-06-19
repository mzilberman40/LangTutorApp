import pytest
from unittest.mock import patch
from learning.models import LexicalUnit, ValidationStatus
from learning.tasks import validate_lu_integrity_async

pytestmark = pytest.mark.django_db


@patch("learning.tasks.get_lemma_details")
def test_validation_task_sets_status_to_valid(mock_get_details, lexical_unit_factory):
    """
    Тестирует сценарий, когда POS в базе данных совпадает с вариантом от LLM.
    Статус должен стать 'valid'.
    """
    # Arrange: LLM возвращает вариант, совпадающий с нашим
    mock_get_details.return_value = [
        {"part_of_speech": "noun", "pronunciation": "/test/"}
    ]
    unit = lexical_unit_factory(lemma="test", part_of_speech="noun")
    assert unit.validation_status == ValidationStatus.UNVERIFIED

    # Act: Запускаем задачу валидации
    validate_lu_integrity_async(unit.id)

    # Assert: Статус изменился на 'valid'
    unit.refresh_from_db()
    assert unit.validation_status == ValidationStatus.VALID
    assert unit.validation_notes == ""


@patch("learning.tasks.get_lemma_details")
def test_validation_task_sets_status_to_mismatch(
    mock_get_details, lexical_unit_factory
):
    """
    Тестирует сценарий, когда POS в базе данных НЕ совпадает с вариантами от LLM.
    Статус должен стать 'mismatch', и должны быть добавлены заметки.
    """
    # Arrange: LLM предлагает 'verb', а в базе сохранено 'noun'
    mock_get_details.return_value = [
        {"part_of_speech": "verb", "pronunciation": "/test/"}
    ]
    unit = lexical_unit_factory(lemma="test", part_of_speech="noun")
    assert unit.validation_status == ValidationStatus.UNVERIFIED

    # Act: Запускаем задачу
    validate_lu_integrity_async(unit.id)

    # Assert: Статус изменился на 'mismatch'
    unit.refresh_from_db()
    assert unit.validation_status == ValidationStatus.MISMATCH
    assert "suggested: [verb]" in unit.validation_notes


@patch("learning.tasks.get_lemma_details")
def test_validation_task_sets_status_to_failed(mock_get_details, lexical_unit_factory):
    """

    Тестирует сценарий, когда LLM не возвращает никаких вариантов (например, для бессмысленной леммы).
    Статус должен стать 'failed'.
    """
    # Arrange: LLM ничего не нашел
    mock_get_details.return_value = []
    unit = lexical_unit_factory(lemma="asdfghjkl", part_of_speech="noun")
    assert unit.validation_status == ValidationStatus.UNVERIFIED

    # Act: Запускаем задачу
    validate_lu_integrity_async(unit.id)

    # Assert: Статус изменился на 'failed'
    unit.refresh_from_db()
    assert unit.validation_status == ValidationStatus.FAILED
    assert "LLM did not return any valid variants" in unit.validation_notes


@patch("learning.signals.validate_lu_integrity_async.delay")
def test_post_save_signal_triggers_validation_task(mock_task_delay, default_user):
    """
    Тестирует, что сигнал post_save корректно запускает нашу задачу Celery.
    Мы "мокаем" саму задачу, чтобы проверить факт ее вызова.
    """
    # Act: Просто создаем новый объект LexicalUnit. Сигнал должен сработать автоматически.
    LexicalUnit.objects.create(
        user=default_user, lemma="signal_test", language="en", part_of_speech="noun"
    )

    # Assert: Проверяем, что метод .delay() нашей задачи был вызван ровно один раз.
    mock_task_delay.assert_called_once()
