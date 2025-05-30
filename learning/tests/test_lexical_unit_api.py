import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from learning.models import LexicalUnit


@pytest.mark.django_db
class TestLexicalUnitAPI:

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("lexicalunit-list")  # uses router-generated name

    def test_create_word(self):
        payload = {"lemma": "fuck off", "language": "en"}
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        assert LexicalUnit.objects.filter(lemma="fuck off").exists()

    def test_create_lexical_unit_with_status_and_notes(self):
        payload = {
            "lemma": "pineapple",
            "language": "en-GB",
            "status": "to_review",
            "notes": "Looks funny",
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        data = response.data
        assert data["lemma"] == "pineapple"
        assert data["status"] == "to_review"
        assert data["notes"] == "Looks funny"

    def test_get_unit_list(self):
        LexicalUnit.objects.create(lemma="apple", language="en")
        LexicalUnit.objects.create(lemma="яблоко", language="ru")
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert len(response.data) >= 2

    def test_update_unit(self):
        unit = LexicalUnit.objects.create(lemma="apple", language="en")
        update_url = reverse("lexicalunit-detail", args=[unit.id])
        response = self.client.put(
            update_url, {"lemma": "apple", "language": "en"}, format="json"
        )
        assert response.status_code == 200
        unit.refresh_from_db()
        assert unit.lemma == "apple"

    def test_delete_word(self):
        unit = LexicalUnit.objects.create(lemma="delete-me", language="en")
        delete_url = reverse("lexicalunit-detail", args=[unit.id])
        response = self.client.delete(delete_url)
        assert response.status_code == 204
        assert not LexicalUnit.objects.filter(id=unit.id).exists()

    def test_bulk_create_lexical_unitss(self):
        payload = [
            {"lemma": "apple", "language": "en-GB"},
            {"lemma": "банан", "language": "ru"},
            {"lemma": "fuck off", "language": "en-GB"},
        ]
        response = self.client.post(self.url, payload, format="json")
        print(response.data)
        assert response.status_code == 201
        # Can be a list or dict, depending on DRF version and serializer
        assert isinstance(response.data, list)
        assert len(response.data) == 3
        units = {u["lemma"] for u in response.data}
        assert "apple" in units
        assert "банан" in units
        assert "fuck off" in units
