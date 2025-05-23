import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from learning.models import Word

pytestmark = pytest.mark.django_db
client = APIClient()


def test_study_words_endpoint_adds_words():
    url = reverse("study-words")
    payload = {"language": "en_GB", "words": ["Outshine", "Brilliant"]}

    response = client.post(url, payload, format="json")
    assert response.status_code == 201
    assert set(response.data["added"]) == {"outshine", "brilliant"}

    assert Word.objects.filter(text="outshine", language="en_GB").exists()
    assert Word.objects.filter(text="brilliant", language="en_GB").exists()


def test_study_words_rejects_empty_list():
    url = reverse("study-words")
    payload = {"language": "en_GB", "words": []}

    response = client.post(url, payload, format="json")
    assert response.status_code == 400
    assert "words" in response.data


def test_study_words_defaults_to_en_GB():
    url = reverse("study-words")
    payload = {"words": ["Effortless"]}

    response = client.post(url, payload, format="json")
    assert response.status_code == 201
    assert "effortless" in response.data["added"]

    word = Word.objects.get(text="effortless")
    assert word.language == "en_GB"
