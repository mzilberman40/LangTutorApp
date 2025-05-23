import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from learning.models import Word


@pytest.mark.django_db
class TestWordAPI:

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("word-list")  # uses router-generated name

    def test_create_word(self):
        payload = {"text": "apple", "language": "en"}
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        assert Word.objects.filter(text="apple").exists()

    def test_get_word_list(self):
        Word.objects.create(text="apple", language="en")
        Word.objects.create(text="яблоко", language="ru")
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert len(response.data) >= 2

    def test_update_word(self):
        word = Word.objects.create(text="appl", language="en")
        update_url = reverse("word-detail", args=[word.id])
        response = self.client.put(
            update_url, {"text": "apple", "language": "en"}, format="json"
        )
        assert response.status_code == 200
        word.refresh_from_db()
        assert word.text == "apple"

    def test_delete_word(self):
        word = Word.objects.create(text="delete-me", language="en")
        delete_url = reverse("word-detail", args=[word.id])
        response = self.client.delete(delete_url)
        assert response.status_code == 204
        assert not Word.objects.filter(id=word.id).exists()
