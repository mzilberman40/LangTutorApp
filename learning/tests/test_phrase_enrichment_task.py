# Создайте новый файл: learning/tests/test_phrase_enrichment_task.py

import pytest
from unittest.mock import patch, MagicMock
from learning.models import Phrase, ValidationStatus
from learning.enums import CEFR, PhraseCategory
from learning.tasks import enrich_phrase_async

pytestmark = pytest.mark.django_db


@patch("learning.tasks.enrich_phrase_details")
def test_enrich_fills_empty_fields_for_valid_phrase(
    mock_enrich_details, phrase_factory
):
    """
    Tests that the task correctly fills empty cefr and category fields
    for a valid phrase.
    """
    # Arrange
    phrase = phrase_factory(
        text="This is a test phrase.", language="en", cefr=None, category=None
    )
    mock_enrich_details.return_value = MagicMock(
        is_valid=True,
        justification=None,
        language_code="en-US",
        cefr_level=CEFR.B1,
        category=PhraseCategory.GENERAL,
    )

    # Act
    enrich_phrase_async(phrase_id=phrase.id)

    # Assert
    phrase.refresh_from_db()
    assert phrase.validation_status == ValidationStatus.VALID
    assert phrase.cefr == CEFR.B1
    assert phrase.category == PhraseCategory.GENERAL
    assert phrase.validation_notes == ""


@patch("learning.tasks.enrich_phrase_details")
def test_enrich_handles_incorrect_phrase(mock_enrich_details, phrase_factory):
    """
    Tests that the task sets MISMATCH status and notes for an incorrect phrase.
    """
    # Arrange
    phrase = phrase_factory(text="It are a good day.", language="en")
    mock_enrich_details.return_value = MagicMock(
        is_valid=False,
        justification="Grammatical error: subject-verb agreement.",
        language_code="en-US",
        cefr_level=CEFR.A1,
        category=PhraseCategory.GENERAL,
    )

    # Act
    enrich_phrase_async(phrase_id=phrase.id)

    # Assert
    phrase.refresh_from_db()
    assert phrase.validation_status == ValidationStatus.MISMATCH
    assert "Grammatical error" in phrase.validation_notes


@patch("learning.tasks.enrich_phrase_details")
def test_enrich_handles_language_mismatch(mock_enrich_details, phrase_factory):
    """
    Tests that the task correctly identifies and notes a language mismatch.
    """
    # Arrange
    phrase = phrase_factory(text="Hola mundo", language="fr")  # Saved as French
    mock_enrich_details.return_value = MagicMock(
        is_valid=True,
        justification="Language mismatch detected.",  # Mock justification
        language_code="es",  # Detected as Spanish
        cefr_level=CEFR.A1,
        category=PhraseCategory.GENERAL,
    )

    # Act
    enrich_phrase_async(phrase_id=phrase.id)

    # Assert
    phrase.refresh_from_db()
    assert phrase.validation_status == ValidationStatus.MISMATCH
    assert (
        "Language mismatch: saved as 'fr', but detected as 'es'"
        in phrase.validation_notes
    )


@patch("learning.tasks.enrich_phrase_details")
def test_enrich_handles_dialect_nuance(mock_enrich_details, phrase_factory):
    """
    Tests that the task adds a note for a dialect nuance without changing status to MISMATCH.
    """
    # Arrange
    phrase = phrase_factory(text="Let's grab a flat white.", language="en")
    mock_enrich_details.return_value = MagicMock(
        is_valid=True,
        justification="Note: This phrasing is typical of Australian English (en-AU).",
        language_code="en-AU",
        cefr_level=CEFR.A2,
        category=PhraseCategory.GENERAL,
    )

    # Act
    enrich_phrase_async(phrase_id=phrase.id)

    # Assert
    phrase.refresh_from_db()
    assert phrase.validation_status == ValidationStatus.VALID  # Status is still valid
    assert "typical of Australian English" in phrase.validation_notes


@patch("learning.tasks.enrich_phrase_details")
def test_enrich_handles_service_failure(mock_enrich_details, phrase_factory):
    """
    Tests that the task sets FAILED status if the enrichment service returns None.
    """
    # Arrange
    phrase = phrase_factory()
    mock_enrich_details.return_value = None

    # Act
    enrich_phrase_async(phrase_id=phrase.id)

    # Assert
    phrase.refresh_from_db()
    assert phrase.validation_status == ValidationStatus.FAILED
    assert "Enrichment process failed" in phrase.validation_notes
