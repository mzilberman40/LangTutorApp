# In new file: learning/tests/test_translation_verification.py

import pytest
from unittest.mock import patch, MagicMock
from learning.models import LexicalUnitTranslation, ValidationStatus
from learning.tasks import verify_translation_link_async

pytestmark = pytest.mark.django_db


# Фикстура для создания объекта перевода
@pytest.fixture
def translation_link(lexical_unit_factory):
    source_lu = lexical_unit_factory(
        lemma="source", language="en", part_of_speech="noun"
    )
    target_lu = lexical_unit_factory(
        lemma="target", language="ru", part_of_speech="noun"
    )
    return LexicalUnitTranslation.objects.create(
        source_unit=source_lu, target_unit=target_lu
    )


@patch("learning.tasks.get_translation_verification")
def test_verification_task_sets_status_valid(mock_get_verification, translation_link):
    """Тест: задача устанавливает статус VALID при высоком балле от сервиса."""
    # Arrange: сервис возвращает Pydantic-объект с высоким баллом
    mock_get_verification.return_value = MagicMock(
        quality_score=5, justification="Perfect translation."
    )
    assert translation_link.validation_status == ValidationStatus.UNVERIFIED

    # Act: Запускаем задачу
    verify_translation_link_async(translation_link.id)

    # Assert: Статус обновлен на VALID
    translation_link.refresh_from_db()
    assert translation_link.validation_status == ValidationStatus.VALID
    assert translation_link.validation_notes == "Perfect translation."


@patch("learning.tasks.get_translation_verification")
def test_verification_task_sets_status_mismatch(
    mock_get_verification, translation_link
):
    """Тест: задача устанавливает статус MISMATCH при среднем балле."""
    # Arrange: сервис возвращает средний балл
    mock_get_verification.return_value = MagicMock(
        quality_score=3, justification="Acceptable but awkward."
    )

    # Act
    verify_translation_link_async(translation_link.id)

    # Assert
    translation_link.refresh_from_db()
    assert translation_link.validation_status == ValidationStatus.MISMATCH


@patch("learning.tasks.get_translation_verification")
def test_verification_task_sets_status_failed_on_low_score(
    mock_get_verification, translation_link
):
    """Тест: задача устанавливает статус FAILED при низком балле."""
    # Arrange: сервис возвращает низкий балл
    mock_get_verification.return_value = MagicMock(
        quality_score=1, justification="Completely wrong."
    )

    # Act
    verify_translation_link_async(translation_link.id)

    # Assert
    translation_link.refresh_from_db()
    assert translation_link.validation_status == ValidationStatus.FAILED


@patch("learning.tasks.get_translation_verification")
def test_verification_task_handles_service_failure(
    mock_get_verification, translation_link
):
    """Тест: задача устанавливает статус FAILED, если сервис вернул None."""
    # Arrange: сервис не смог вернуть результат
    mock_get_verification.return_value = None

    # Act
    verify_translation_link_async(translation_link.id)

    # Assert
    translation_link.refresh_from_db()
    assert translation_link.validation_status == ValidationStatus.FAILED
    assert (
        "Verification service did not return a valid response"
        in translation_link.validation_notes
    )


@patch("learning.signals.verify_translation_link_async.delay")
def test_signal_triggers_verification_task(mock_task_delay, lexical_unit_factory):
    """Тест: сигнал post_save для LexicalUnitTranslation запускает задачу."""
    # Arrange
    source_lu = lexical_unit_factory(
        lemma="source", language="en", part_of_speech="noun"
    )
    target_lu = lexical_unit_factory(
        lemma="target", language="ru", part_of_speech="noun"
    )

    # Act: Просто создаем объект, сигнал должен сработать
    LexicalUnitTranslation.objects.create(source_unit=source_lu, target_unit=target_lu)

    # Assert: Проверяем, что метод .delay() задачи был вызван один раз
    mock_task_delay.assert_called_once()
