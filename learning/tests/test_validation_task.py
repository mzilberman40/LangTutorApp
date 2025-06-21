# Пожалуйста, полностью замените содержимое этого файла.
import pytest
from unittest.mock import patch
from learning.models import LexicalUnit, ValidationStatus
from learning.tasks import validate_lu_integrity_async

pytestmark = pytest.mark.django_db


@patch("learning.tasks.get_lemma_details")
def test_validation_task_sets_status_to_valid(mock_get_details, lexical_unit_factory):
    mock_get_details.return_value = [
        {
            "lexical_category": "SINGLE_WORD",
            "part_of_speech": "noun",
            "pronunciation": "/test/",
        }
    ]
    unit = lexical_unit_factory(lemma="test", part_of_speech="noun")
    assert unit.validation_status == ValidationStatus.UNVERIFIED
    validate_lu_integrity_async(unit.id)
    unit.refresh_from_db()
    assert unit.validation_status == ValidationStatus.VALID
    assert unit.validation_notes == ""


@patch("learning.tasks.get_lemma_details")
def test_validation_task_sets_status_to_mismatch(
    mock_get_details, lexical_unit_factory
):
    mock_get_details.return_value = [
        {
            "lexical_category": "SINGLE_WORD",
            "part_of_speech": "verb",
            "pronunciation": "/test/",
        }
    ]
    unit = lexical_unit_factory(lemma="test", part_of_speech="noun")
    validate_lu_integrity_async(unit.id)
    unit.refresh_from_db()
    assert unit.validation_status == ValidationStatus.MISMATCH
    assert "suggested: [verb]" in unit.validation_notes


@patch("learning.tasks.get_lemma_details")
def test_validation_task_sets_status_to_failed(mock_get_details, lexical_unit_factory):
    mock_get_details.return_value = []
    unit = lexical_unit_factory(lemma="asdfghjkl", part_of_speech="noun")
    validate_lu_integrity_async(unit.id)
    unit.refresh_from_db()
    assert unit.validation_status == ValidationStatus.FAILED
    assert "LLM did not return any valid variants" in unit.validation_notes


@patch("learning.signals.validate_lu_integrity_async.delay")
def test_post_save_signal_triggers_validation_task(mock_task_delay, default_user):
    LexicalUnit.objects.create(
        user=default_user, lemma="signal_test", language="en", part_of_speech="noun"
    )
    mock_task_delay.assert_called_once()
