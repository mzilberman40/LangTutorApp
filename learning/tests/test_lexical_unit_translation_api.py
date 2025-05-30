import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from learning.models import LexicalUnit, LexicalUnitTranslation

pytestmark = pytest.mark.django_db


class TestLexicalUnitTranslationAPI:
    def setup_method(self):
        self.client = APIClient()
        self.unit1 = LexicalUnit.objects.create(lemma="apple", language="en-GB")
        self.unit2 = LexicalUnit.objects.create(lemma="яблоко", language="ru")
        self.url = reverse("lexicalunittranslation-list")

    def test_create_lexicalunit_translation(self):
        payload = {
            "source_unit": self.unit1.id,
            "target_unit": self.unit2.id,
            "translation_type": "manual",
            "confidence": 0.99,
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        assert LexicalUnitTranslation.objects.filter(
            source_unit=self.unit1, target_unit=self.unit2
        ).exists()

    def test_list_lexicalunit_translations(self):
        LexicalUnitTranslation.objects.create(source_unit=self.unit1, target_unit=self.unit2)
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert any(
            item["source_unit"] == self.unit1.id
            and item["target_unit"] == self.unit2.id
            for item in response.data
        )

    def test_unique_constraint_api(self):
        LexicalUnitTranslation.objects.create(source_unit=self.unit1, target_unit=self.unit2)
        payload = {"source_unit": self.unit1.id, "target_unit": self.unit2.id}
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code in (400, 422)

    def test_delete_lexicalunit_translation(self):
        trans = LexicalUnitTranslation.objects.create(
            source_unit=self.unit1, target_unit=self.unit2
        )
        delete_url = reverse("lexicalunittranslation-detail", args=[trans.id])
        response = self.client.delete(delete_url)
        assert response.status_code == 204
        assert not LexicalUnitTranslation.objects.filter(id=trans.id).exists()

    def test_multiple_translations_allowed(self):
        src = LexicalUnit.objects.create(lemma="run", language="en-GB")
        tgt1 = LexicalUnit.objects.create(lemma="бежать", language="ru")
        tgt2 = LexicalUnit.objects.create(lemma="управлять", language="ru")

        LexicalUnitTranslation.objects.create(source_unit=src, target_unit=tgt1)
        LexicalUnitTranslation.objects.create(source_unit=src, target_unit=tgt2)

        assert LexicalUnitTranslation.objects.filter(source_unit=src).count() == 2

    def test_bulk_create_lexicalunit_translations(self):
        src = LexicalUnit.objects.create(lemma="run", language="en-GB")
        tgt1 = LexicalUnit.objects.create(lemma="бежать", language="ru")
        tgt2 = LexicalUnit.objects.create(lemma="управлять", language="ru")

        bulk_url = reverse("lexicalunittranslation-bulk-create")
        payload = {
            "source_unit": {
                "lemma": "run",
                "language": "en-GB",
                "part_of_speech": "verb",
                "pronunciation": "/rʌn/",
            },
            "targets": [
                {
                    "lemma": "бежать",
                    "language": "ru",
                    "part_of_speech": "verb",
                    "pronunciation": "[бʲɪˈʐatʲ]",
                },
                {
                    "lemma": "управлять",
                    "language": "ru",
                    "part_of_speech": "verb",
                    "pronunciation": "[ʊprɐˈvlʲætʲ]",
                },
            ],
            "translation_type": "manual",
            "confidence": 1.0,
        }
        response = self.client.post(bulk_url, payload, format="json")
        assert response.status_code == 201
        assert LexicalUnitTranslation.objects.filter(
            source_unit=src, target_unit=tgt1
        ).exists()
        assert LexicalUnitTranslation.objects.filter(
            source_unit=src, target_unit=tgt2
        ).exists()