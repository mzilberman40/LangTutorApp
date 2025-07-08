# learning/tests/test_phrase_enrichment_task.py
import pytest
from unittest.mock import patch, MagicMock

from learning.models import Phrase
from learning.enums import ValidationStatus, CEFR, PhraseCategory
from learning.tasks import enrich_phrase_async
from services.enrich_phrase_details import enrich_phrase_details, PhraseAnalysisResponse

pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("no_phrase_enrichment_signal")
def test_enrich_phrase_task_success_path(phrase_factory):
    """
    Tests the enrich_phrase_async task's logic in isolation.
    """
    phrase = phrase_factory(
        text="A test phrase.", language="en", cefr=None, category=None
    )

    mock_analysis_result = PhraseAnalysisResponse(
        is_valid=True,
        justification="Looks natural.",
        language_code="en-US",
        cefr_level=CEFR.B2,
        category=PhraseCategory.GENERAL,
    )

    with patch(
        "learning.tasks.enrich_phrase_details", return_value=mock_analysis_result
    ) as mock_enrich_service:
        enrich_phrase_async(phrase_id=phrase.id)

    phrase.refresh_from_db()

    assert phrase.validation_status == ValidationStatus.VALID


@pytest.mark.usefixtures("no_phrase_enrichment_signal")
def test_enrich_phrase_task_mismatch_path(phrase_factory):
    """
    Tests that the task correctly handles a mismatch scenario.
    """
    phrase = phrase_factory(text="This are bad grammar.", language="en", cefr=CEFR.A1)

    mock_analysis_result = PhraseAnalysisResponse(
        is_valid=False,
        justification="Grammatical error: 'This are' should be 'This is'.",
        language_code="en-GB",
        cefr_level=CEFR.A2,
        category=PhraseCategory.GENERAL,
    )

    with patch(
        "learning.tasks.enrich_phrase_details", return_value=mock_analysis_result
    ):
        enrich_phrase_async(phrase_id=phrase.id)

    phrase.refresh_from_db()
    assert phrase.validation_status == ValidationStatus.MISMATCH
    assert phrase.cefr == CEFR.A1
    assert "Grammatical error" in phrase.validation_notes
    assert "CEFR level mismatch" in phrase.validation_notes


# --- FIX IS HERE: Apply the fixture to this test as well to prevent DB pollution ---
@pytest.mark.usefixtures("no_phrase_enrichment_signal")
@patch("services.enrich_phrase_details.answer_with_llm")
def test_enrich_phrase_service_logic(mock_answer_with_llm, phrase_factory):
    """
    Tests the enrich_phrase_details service's logic in isolation.
    """
    mock_client = MagicMock()
    phrase_to_analyze = phrase_factory(text="A phrase to analyze", language="en")
    llm_json_response = """
    {
        "is_valid": true,
        "justification": "The phrase is grammatically correct and natural.",
        "language_code": "en-US",
        "cefr_level": "B1",
        "category": "GENERAL"
    }
    """
    mock_answer_with_llm.return_value = llm_json_response

    result = enrich_phrase_details(client=mock_client, phrase=phrase_to_analyze)

    assert isinstance(result, PhraseAnalysisResponse)
    assert result.is_valid is True
    assert result.cefr_level == CEFR.B1
    mock_answer_with_llm.assert_called_once()
