# learning/tests/conftest.py

import os
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from unittest.mock import MagicMock, patch

from learning.enums import (
    LexicalCategory,
    PartOfSpeech,
    CEFR,
    PhraseCategory,
    ValidationStatus,
)
from learning.models import LexicalUnit, Phrase


@pytest.fixture(autouse=True, scope="session")
def set_env_for_tests():
    # Keep this, as it sets the env var for general clarity/fallbacks.
    os.environ["NEBIUS_API_KEY"] = "dummy-test-api-key"


# Add global mocks for external services.
# This fixture will ensure all LLM-related calls are mocked across all tests.
@pytest.fixture(autouse=True)
def mock_llm_services():
    # KEY CHANGE: Patch get_client within learning.tasks, as that's where it's used.
    # This mock will be the 'client' object passed to enrich_phrase_details and answer_with_llm.
    mock_client_instance = MagicMock()
    # Configure the mocked client to return a mock completion object with JSON content
    mock_client_instance.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"is_valid": true, "language_code": "en-US", "cefr_level": "B1", "category": "GENERAL", "justification": null}'
                )
            )
        ]
    )

    with patch(
        "learning.tasks.get_client", return_value=mock_client_instance
    ) as mock_get_client_in_tasks:
        # Patch enrich_phrase_details (from services.enrich_phrase_details),
        # as it's used in learning.tasks.
        with patch(
            "services.enrich_phrase_details.enrich_phrase_details",
            return_value=MagicMock(
                is_valid=True,
                justification=None,
                language_code="en-US",
                cefr_level=CEFR.B1,
                category=PhraseCategory.GENERAL,
            ),
        ) as mock_enrich_phrase_details:
            # Patch translate_lemma_with_details (from services.translate_lemma)
            # This is also used in learning.tasks.
            with patch(
                "services.translate_lemma.translate_lemma_with_details",
                return_value=MagicMock(
                    translated_lemma="mocked translation",
                    translation_details=[
                        MagicMock(
                            lexical_category=LexicalCategory.SINGLE_WORD,
                            part_of_speech=PartOfSpeech.NOUN,
                            pronunciation="/mock/",
                        )
                    ],
                ),
            ) as mock_translate_lemma_with_details:
                # Patch get_lemma_details (from services.get_lemma_details)
                # Used in learning.tasks.
                with patch(
                    "services.get_lemma_details.get_lemma_details",
                    return_value=[
                        MagicMock(
                            lexical_category=LexicalCategory.SINGLE_WORD,
                            part_of_speech=PartOfSpeech.NOUN,
                            pronunciation="/mock/",
                        ),
                    ],
                ) as mock_get_lemma_details:
                    # Patch get_translation_verification (from services.verify_translation)
                    # Used in learning.tasks.
                    with patch(
                        "services.verify_translation.get_translation_verification",
                        return_value=MagicMock(
                            quality_score=5, justification="Mocked perfect translation."
                        ),
                    ) as mock_get_translation_verification:
                        # Yield the primary mock and others if they need to be inspected in tests
                        yield mock_get_client_in_tasks, mock_enrich_phrase_details, mock_translate_lemma_with_details, mock_get_lemma_details, mock_get_translation_verification


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    def create_user(username="testuser", password="password123"):
        return User.objects.create_user(username=username, password=password)

    return create_user


@pytest.fixture
def default_user(user_factory):
    return user_factory()


@pytest.fixture
def authenticated_client(api_client, default_user):
    api_client.force_authenticate(user=default_user)
    return api_client


@pytest.fixture
def lexical_unit_factory(db, default_user):
    def create_lu(**kwargs):
        kwargs.setdefault("user", default_user)
        kwargs.setdefault("lexical_category", LexicalCategory.SINGLE_WORD)
        kwargs.setdefault("part_of_speech", PartOfSpeech.NOUN)
        return LexicalUnit.objects.create(**kwargs)

    return create_lu


@pytest.fixture
def phrase_factory(db):
    """A factory for creating Phrase instances."""

    def create_phrase(**kwargs):
        kwargs.setdefault("text", "A default test phrase.")
        kwargs.setdefault("language", "en")
        return Phrase.objects.create(**kwargs)

    return create_phrase
