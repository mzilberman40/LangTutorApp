# learning/tests/conftest.py
import os
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from unittest.mock import patch

from learning.enums import (
    LexicalCategory,
    PartOfSpeech,
    CEFR,
    PhraseCategory,
)
from learning.models import LexicalUnit, Phrase
from services.enrich_phrase_details import PhraseAnalysisResponse
from services.get_lemma_details import CharacterProfile, CharacterProfileResponse
from services.translate_lemma import TranslationDetail, TranslationResponse
from services.verify_translation import TranslationQualityResponse


@pytest.fixture(autouse=True, scope="session")
def set_env_for_tests():
    os.environ["NEBIUS_API_KEY"] = "dummy-test-api-key"


@pytest.fixture(autouse=True)
def mock_llm_services():
    """Globally mocks all high-level services that interact with the LLM."""
    mock_enrich_response = PhraseAnalysisResponse(
        is_valid=True,
        justification=None,
        language_code="en-US",
        cefr_level=CEFR.B1,
        category=PhraseCategory.GENERAL,
    )
    mock_lemma_details_response = CharacterProfileResponse(
        lemma_details=[
            CharacterProfile(
                lexical_category=LexicalCategory.SINGLE_WORD,
                part_of_speech=PartOfSpeech.NOUN,
                pronunciation="/mock/",
            )
        ]
    )
    mock_translate_response = TranslationResponse(
        translated_lemma="mocked translation",
        translation_details=[
            TranslationDetail(
                lexical_category=LexicalCategory.SINGLE_WORD,
                part_of_speech=PartOfSpeech.NOUN,
                pronunciation="/mock/",
            )
        ],
    )
    mock_verify_response = TranslationQualityResponse(
        quality_score=5, justification="Mocked perfect translation."
    )

    with patch(
        "learning.tasks.enrich_phrase_details", return_value=mock_enrich_response
    ) as mock_enrich, patch(
        "learning.tasks.get_lemma_details",
        return_value=[
            d.model_dump() for d in mock_lemma_details_response.lemma_details
        ],
    ) as mock_get_details, patch(
        "learning.tasks.translate_lemma_with_details",
        return_value=mock_translate_response,
    ) as mock_translate, patch(
        "learning.tasks.get_translation_verification", return_value=mock_verify_response
    ) as mock_verify:

        yield mock_enrich, mock_get_details, mock_translate, mock_verify


# --- NEW FIXTURE IMPLEMENTATION ---
@pytest.fixture
def no_phrase_enrichment_signal(monkeypatch):
    """
    A pytest fixture to prevent the phrase enrichment task from running via a signal.
    It uses pytest's monkeypatch to replace the task's .delay() method with a
    function that does nothing. This is a more robust method than disconnecting
    the Django signal.
    """
    # Target the 'delay' method of the task object AS IT IS IMPORTED in the signals module.
    monkeypatch.setattr(
        "learning.signals.enrich_phrase_async.delay", lambda *args, **kwargs: None
    )
    yield


# --- END NEW IMPLEMENTATION ---


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
    def create_phrase(**kwargs):
        kwargs.setdefault("text", "A default test phrase.")
        kwargs.setdefault("language", "en")
        return Phrase.objects.create(**kwargs)

    return create_phrase
