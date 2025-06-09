# In learning/tests/test_phrase_translation_api.py
import pytest
from django.urls import reverse
from learning.models import Phrase, PhraseTranslation

pytestmark = pytest.mark.django_db


class TestPhraseTranslationAPI:
    def test_create_phrase_translation(self, authenticated_client):
        url = reverse("phrasetranslation-list")
        src = Phrase.objects.create(text="Good luck!", language="en", cefr="A2")
        tgt = Phrase.objects.create(text="Удачи!", language="ru", cefr="A2")
        data = {"source_phrase": src.id, "target_phrase": tgt.id}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == 201
        assert PhraseTranslation.objects.filter(source_phrase=src).exists()

    def test_translation_self_blocked(self, authenticated_client):
        url = reverse("phrasetranslation-list")
        src = Phrase.objects.create(text="Good luck!", language="en", cefr="A2")
        data = {"source_phrase": src.id, "target_phrase": src.id}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == 400
        assert "cannot translate to itself" in str(response.data).lower()
