# learning/tests/test_phrase_api.py
import pytest
from django.urls import reverse
from unittest.mock import patch, MagicMock
from learning.models import Phrase
from learning.enums import CEFR, PhraseCategory, ValidationStatus
import logging
import uuid  # Import the uuid module to validate UUIDs

logger = logging.getLogger(__name__)

# All tests in this file will be run against the database
pytestmark = pytest.mark.django_db


class TestPhraseAPI:
    def test_create_phrase(self, authenticated_client):
        url = reverse("phrase-list")
        data = {
            "text": "Break a leg!",
            "language": "en",
            "category": "IDIOM",
            "cefr": "B2",
        }
        response = authenticated_client.post(url, data, format="json")
        assert response.status_code == 201
        assert Phrase.objects.filter(text="Break a leg!", language="en").exists()

    def test_create_phrase_with_optional_fields_omitted(self, authenticated_client):
        """Tests that a phrase can be created without CEFR and category."""
        url = reverse("phrase-list")
        data = {"text": "An incomplete phrase.", "language": "en"}
        response = authenticated_client.post(url, data, format="json")
        assert response.status_code == 201
        phrase = Phrase.objects.get(id=response.data["id"])
        assert phrase.cefr is None
        assert phrase.category is None

    def test_get_phrase_list(self, authenticated_client, phrase_factory):
        url = reverse("phrase-list")
        phrase_factory()  # Create a phrase to ensure the list is not empty
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert len(response.data) >= 1

    # We are NOT patching the task function or its delay method here.
    # We rely on CELERY_TASK_ALWAYS_EAGER=True (in settings.py) to run the real task.
    # We rely on GLOBAL mocks in conftest.py to mock LLM service calls within the real task.
    def test_enrich_endpoint_triggers_task(self, authenticated_client, phrase_factory):
        """
        Tests that the /enrich/ endpoint correctly triggers the phrase enrichment task.
        In eager mode, this verifies the real task is called and its effects are applied.
        """
        logger.debug("Starting test_enrich_endpoint_triggers_task")

        phrase = phrase_factory()
        url = reverse("phrase-enrich", kwargs={"pk": phrase.pk})

        logger.debug(f"Calling API endpoint {url}")
        response = authenticated_client.post(url)
        logger.debug("API endpoint call finished.")

        # Assert API response
        assert response.status_code == 202
        assert "task_id" in response.data
        # Assert that task_id is a valid UUID, not a specific mocked string.
        # This is the pragmatic approach when Celery eager mode generates real UUIDs.
        try:
            uuid.UUID(response.data["task_id"], version=4)  # Validate as UUIDv4
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False
        assert (
            is_valid_uuid
        ), f"Expected task_id to be a valid UUID, but got {response.data['task_id']}"

        # Since Celery is in eager mode (configured in settings.py),
        # the real enrich_phrase_async task will have run and updated the phrase.
        # We need to refresh the phrase object from the database to see the changes.
        phrase.refresh_from_db()

        # Assert on the phrase's updated state, relying on the real task's logic
        # (which itself relies on global mocks from conftest.py)
        assert phrase.validation_status == ValidationStatus.VALID
        assert phrase.cefr == CEFR.B1
        assert phrase.category == PhraseCategory.GENERAL
        assert phrase.validation_notes == ""
        logger.debug("Test finished successfully.")
