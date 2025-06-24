# Пожалуйста, полностью замените содержимое этого файла.
import pytest
from django.urls import reverse
from unittest.mock import patch, MagicMock

from learning.enums import ValidationStatus, PhraseCategory, CEFR
from learning.models import Phrase

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
