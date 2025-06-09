# In learning/tests/test_phrase_api.py
import pytest
from django.urls import reverse
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

    def test_get_phrase_list(self, authenticated_client):
        url = reverse("phrase-list")
        Phrase.objects.create(
            text="Good luck!", language="en", category="GENERAL", cefr="A2"
        )

        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert len(response.data) >= 1
