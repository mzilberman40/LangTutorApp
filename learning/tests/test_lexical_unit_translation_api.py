# In learning/tests/test_lexical_unit_translation_api.py
import pytest
from django.urls import reverse
from learning.models import LexicalUnit, LexicalUnitTranslation
from learning.enums import PartOfSpeech

pytestmark = pytest.mark.django_db


# The `authenticated_client` fixture handles creating a user and logging them in.
# The `lexical_unit_factory` fixture handles creating LUs for that user.
class TestLexicalUnitTranslationAPI:

    def test_create_lexicalunit_translation(
        self, authenticated_client, lexical_unit_factory
    ):
        # Create the test objects using the factory inside the test
        unit1 = lexical_unit_factory(
            lemma="apple", language="en-GB", part_of_speech=PartOfSpeech.NOUN
        )
        unit2 = lexical_unit_factory(
            lemma="яблоко", language="ru", part_of_speech=PartOfSpeech.NOUN
        )
        url = reverse("lexicalunittranslation-list")

        payload = {
            "source_unit": unit1.id,
            "target_unit": unit2.id,
            "translation_type": "manual",
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201
        assert LexicalUnitTranslation.objects.filter(
            source_unit=unit1, target_unit=unit2
        ).exists()

    def test_list_lexicalunit_translations(
        self, authenticated_client, lexical_unit_factory
    ):
        unit1 = lexical_unit_factory(
            lemma="apple", language="en-GB", part_of_speech=PartOfSpeech.NOUN
        )
        unit2 = lexical_unit_factory(
            lemma="яблоко", language="ru", part_of_speech=PartOfSpeech.NOUN
        )
        url = reverse("lexicalunittranslation-list")

        LexicalUnitTranslation.objects.create(source_unit=unit1, target_unit=unit2)
        response = authenticated_client.get(url)

        assert response.status_code == 200
        # The queryset for this view is not user-filtered yet, so we just check for existence.
        assert any(
            item["source_unit"] == unit1.id and item["target_unit"] == unit2.id
            for item in response.data
        )

    def test_delete_lexicalunit_translation(
        self, authenticated_client, lexical_unit_factory
    ):
        unit1 = lexical_unit_factory(
            lemma="apple", language="en-GB", part_of_speech=PartOfSpeech.NOUN
        )
        unit2 = lexical_unit_factory(
            lemma="яблоко", language="ru", part_of_speech=PartOfSpeech.NOUN
        )
        trans = LexicalUnitTranslation.objects.create(
            source_unit=unit1, target_unit=unit2
        )

        delete_url = reverse("lexicalunittranslation-detail", args=[trans.id])
        response = authenticated_client.delete(delete_url)
        assert response.status_code == 204
        assert not LexicalUnitTranslation.objects.filter(id=trans.id).exists()

    def test_bulk_create_lexicalunit_translations(self, authenticated_client):
        # This test doesn't need to pre-create any units, because the bulk payload
        # creates them automatically. We just need an authenticated client to send the request.
        bulk_url = reverse("lexicalunittranslation-bulk-create")
        payload = {
            "source_unit": {
                "lemma": "run fast",
                "language": "en-GB",
                "part_of_speech": "phrasal_verb",
            },
            "targets": [
                {"lemma": "бежать быстро", "language": "ru", "part_of_speech": "verb"},
                {"lemma": "course rapide", "language": "fr", "part_of_speech": "noun"},
            ],
        }

        response = authenticated_client.post(bulk_url, payload, format="json")
        assert response.status_code == 201

        # Verify that the objects were created and linked correctly.
        source_lu = LexicalUnit.objects.get(lemma="run fast", language="en-GB")
        target_lu1 = LexicalUnit.objects.get(lemma="бежать быстро", language="ru")
        assert LexicalUnitTranslation.objects.filter(
            source_unit=source_lu, target_unit=target_lu1
        ).exists()
