import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from learning.models import Phrase, PhraseTranslation

pytestmark = pytest.mark.django_db


class TestPhraseTranslationAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("phrasetranslation-list")
        self.src = Phrase.objects.create(
            text="Good luck!", language="en", category="GENERAL", cefr="A2"
        )
        self.tgt = Phrase.objects.create(
            text="Удачи!", language="ru", category="GENERAL", cefr="A2"
        )

    def test_create_phrase_translation(self):
        data = {
            "source_phrase": self.src.id,
            "target_phrase": self.tgt.id,
        }
        response = self.client.post(self.url, data, format="json")
        assert response.status_code == 201
        assert PhraseTranslation.objects.filter(source_phrase=self.src).exists()

    def test_list_phrase_translations(self):
        PhraseTranslation.objects.create(source_phrase=self.src, target_phrase=self.tgt)
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_translation_self_blocked(self):
        data = {
            "source_phrase": self.src.id,
            "target_phrase": self.src.id,
        }
        response = self.client.post(self.url, data, format="json")
        assert response.status_code == 400
        assert "cannot translate to itself" in str(response.data).lower()
