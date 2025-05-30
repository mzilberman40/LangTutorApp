import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from learning.models import Phrase

pytestmark = pytest.mark.django_db


class TestPhraseAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("phrase-list")

    def test_create_phrase(self):
        data = {
            "text": "Break a leg!",
            "language": "en",
            "category": "IDIOM",
            "cefr": "B2",
        }
        response = self.client.post(self.url, data, format="json")
        assert response.status_code == 201
        assert Phrase.objects.filter(text="Break a leg!", language="en").exists()

    def test_get_phrase_list(self):
        Phrase.objects.create(
            text="Good luck!", language="en", category="GENERAL", cefr="A2"
        )
        Phrase.objects.create(
            text="Удачи!", language="ru", category="GENERAL", cefr="A2"
        )
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert len(response.data) >= 2
