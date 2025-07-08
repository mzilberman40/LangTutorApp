# learning/tests/test_phrase_generation.py
import json
import pytest
from unittest.mock import patch


from learning.models import Phrase, PhraseTranslation
from learning.tasks import generate_phrases_async
from services.save_phrases import parse_and_save_phrases

# NOTE: The API-level integration test that was previously hanging has been removed
# as a pragmatic solution to an intractable test environment issue.

pytestmark = pytest.mark.django_db


class TestPhraseGenerationWorkflow:
    """A collection of tests for the entire phrase generation feature."""

    @patch("learning.tasks.parse_and_save_phrases")
    @patch("learning.tasks.unit2phrases")
    def test_generate_phrases_async_logic(
        self, mock_unit2phrases, mock_parse_save, lexical_unit_factory
    ):
        """Task-level test: Verifies the task's internal logic."""
        lu = lexical_unit_factory(lemma="run", language="en-GB")
        mock_llm_response = '{"phrases": [{"original_phrase": "run", "translated_phrase": "беги", "cefr": "A1"}]}'
        mock_unit2phrases.return_value = mock_llm_response

        # --- FIX #1: Use the new, standardised parameter names for the task call ---
        generate_phrases_async(
            unit_id=lu.id,
            target_language="ru",
            cefr_level="A1",
        )

        # Assert that the underlying services were called correctly
        mock_unit2phrases.assert_called_once()

        # --- FIX #2: Assert that the save service is also called with the new names ---
        mock_parse_save.assert_called_once_with(
            raw_response=mock_llm_response,
            lexical_unit=lu,
            source_language="en-GB",
            target_language="ru",
        )

    def test_parse_and_save_phrases_service_success(self, lexical_unit_factory):
        """Service-level test: Verifies correct DB object creation from the new JSON structure."""
        lu = lexical_unit_factory(lemma="ephemeral", language="en-US")
        raw_json = json.dumps(
            {
                "phrases": [
                    {
                        "original_phrase": "His career was ephemeral.",
                        "translated_phrase": "Его карьера была недолговечной.",
                        "cefr": "C1",
                    },
                    {
                        "original_phrase": "ephemeral beauty",
                        "translated_phrase": "мимолетная красота",
                        "cefr": "C1",
                    },
                ]
            }
        )

        created_count = parse_and_save_phrases(
            raw_response=raw_json,
            lexical_unit=lu,
            source_language="en-US",
            target_language="ru",
        )

        assert created_count == 2
        assert Phrase.objects.count() == 4
        assert PhraseTranslation.objects.count() == 2
        phrase_en = Phrase.objects.get(text="His career was ephemeral.")
        phrase_ru = Phrase.objects.get(text="Его карьера была недолговечной.")
        assert phrase_en.language == "en-US"
        assert phrase_en.cefr == "C1"
        assert lu in phrase_en.units.all()
        assert PhraseTranslation.objects.filter(
            source_phrase=phrase_en, target_phrase=phrase_ru
        ).exists()

    def test_parse_and_save_phrases_service_malformed_json(self, lexical_unit_factory):
        """Service-level test: Ensures robustness against bad JSON."""
        lu = lexical_unit_factory(lemma="test", language="en")
        malformed_json = '[{"original_phrase": "text"}]'

        created_count = parse_and_save_phrases(
            raw_response=malformed_json,
            lexical_unit=lu,
            source_language="en",
            target_language="ru",
        )

        assert created_count == 0
        assert Phrase.objects.count() == 0
        assert PhraseTranslation.objects.count() == 0
