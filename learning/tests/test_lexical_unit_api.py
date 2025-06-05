# In learning/tests/test_lexical_unit_api.py
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from learning.models import LexicalUnit
from learning.enums import (
    LexicalUnitType,
    PartOfSpeech,
    LexicalUnitStatus,
)  # Assuming correct enum names


@pytest.mark.django_db
class TestLexicalUnitAPI:

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("lexicalunit-list")  # from learning.urls router basename

    def test_create_lexical_unit_single_word(self):
        payload = {
            "lemma": "  TesTWord  ",
            "language": "en-GB",
            "part_of_speech": PartOfSpeech.NOUN,
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        data = response.data
        assert data["lemma"] == "testword"  # Canonical: lowercase, stripped
        assert data["language"] == "en-GB"
        assert data["part_of_speech"] == PartOfSpeech.NOUN
        assert data["unit_type"] == LexicalUnitType.SINGLE
        assert LexicalUnit.objects.filter(
            lemma="testword", language="en-GB", part_of_speech=PartOfSpeech.NOUN
        ).exists()

    def test_create_lexical_unit_collocation(self):
        payload = {
            "lemma": "  TesT   COLLOCATION  ",
            "language": "en",
            "part_of_speech": PartOfSpeech.COLLOCATION,
        }  # Assuming COLLOCATION is in PartOfSpeech
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        data = response.data
        assert data["lemma"] == "test collocation"  # Canonical
        assert data["unit_type"] == LexicalUnitType.COLLOC
        assert data["part_of_speech"] == PartOfSpeech.COLLOCATION
        assert LexicalUnit.objects.filter(
            lemma="test collocation",
            language="en",
            part_of_speech=PartOfSpeech.COLLOCATION,
        ).exists()

    def test_create_lexical_unit_default_pos(self):
        # Tests creation when part_of_speech is not provided, relying on model default ""
        payload = {"lemma": "default pos test", "language": "de"}
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        data = response.data
        assert data["lemma"] == "default pos test"
        assert data["part_of_speech"] == ""  # Default from model
        assert data["unit_type"] == LexicalUnitType.COLLOC
        assert LexicalUnit.objects.filter(
            lemma="default pos test", language="de", part_of_speech=""
        ).exists()

    def test_create_lexical_unit_with_status_and_notes(self):
        payload = {
            "lemma": "  Pineapple王国 ",  # Mixed case, spaces, non-ASCII
            "language": "ja",
            "part_of_speech": PartOfSpeech.NOUN,
            "status": LexicalUnitStatus.TO_REVIEW,  # Use your enum
            "notes": "Exotic and regal",
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        data = response.data
        assert (
            data["lemma"] == "pineapple王国"
        )  # Canonical: lowercase, single space, original chars preserved
        assert data["part_of_speech"] == PartOfSpeech.NOUN
        assert data["status"] == LexicalUnitStatus.TO_REVIEW
        assert data["notes"] == "Exotic and regal"
        assert data["unit_type"] == LexicalUnitType.COLLOC  # Due to space

    def test_create_duplicate_lexical_unit_fails(self):
        # Test unique_together ("lemma", "language", "part_of_speech") via API
        common_payload = {
            "lemma": "unique_test",
            "language": "es",
            "part_of_speech": PartOfSpeech.VERB,
        }
        response1 = self.client.post(self.url, common_payload, format="json")
        assert response1.status_code == 201

        # Attempt to create exact duplicate
        response2 = self.client.post(self.url, common_payload, format="json")
        assert response2.status_code == 400  # DRF validation for unique_together

        # Attempt with different case (should also fail due to .lower() in save)
        payload_diff_case = {
            "lemma": "Unique_Test",
            "language": "es",
            "part_of_speech": PartOfSpeech.VERB,
        }
        response3 = self.client.post(self.url, payload_diff_case, format="json")
        assert response3.status_code == 400

    def test_get_lexical_unit_list(self):
        LexicalUnit.objects.create(
            lemma="apple", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        LexicalUnit.objects.create(
            lemma="яблоко", language="ru", part_of_speech=PartOfSpeech.NOUN
        )
        response = self.client.get(self.url)
        assert response.status_code == 200
        # Ensure data is a list (standard for list views)
        assert isinstance(response.data, list)
        # Adjust count based on pagination or other fixtures. Here expecting at least 2.
        assert len(response.data) >= 2

    def test_update_lexical_unit(self):
        lu = LexicalUnit.objects.create(
            lemma="original",
            language="en",
            part_of_speech=PartOfSpeech.NOUN,
            notes="old note",
        )
        update_url = reverse("lexicalunit-detail", args=[lu.id])

        # PUT requires all fields for a full update, or use PATCH for partial.
        # Let's test updating notes and status, lemma and language could also be updatable.
        # The original lemma was "original", so canonical form is "original".
        payload_to_update = {
            "lemma": "ORIGINAL",  # Will be canonicalized to "original"
            "language": "en",
            "part_of_speech": PartOfSpeech.NOUN,  # Must match for unique constraint if lemma/lang are same
            "status": LexicalUnitStatus.KNOWN,
            "notes": "new note",
            "pronunciation": "/əˈrɪdʒɪnəl/",  # Assuming pronunciation can be updated
            # unit_type is read-only or set by save()
        }
        response = self.client.put(update_url, payload_to_update, format="json")
        assert response.status_code == 200
        lu.refresh_from_db()
        assert lu.lemma == "original"  # Canonicalized
        assert lu.notes == "new note"
        assert lu.status == LexicalUnitStatus.KNOWN
        assert lu.pronunciation == "/əˈrɪdʒɪnəl/"
        assert lu.unit_type == LexicalUnitType.SINGLE  # Based on canonical "original"

    def test_delete_lexical_unit(self):
        # Renamed from test_delete_word for consistency
        unit = LexicalUnit.objects.create(
            lemma="delete-me", language="en", part_of_speech=""
        )
        delete_url = reverse("lexicalunit-detail", args=[unit.id])
        response = self.client.delete(delete_url)
        assert response.status_code == 204
        assert not LexicalUnit.objects.filter(id=unit.id).exists()

    def test_bulk_create_lexical_units(self):
        # Renamed from test_bulk_create_lexical_unitss
        payload = [
            {
                "lemma": "  Apple Tree  ",
                "language": "en-GB",
                "part_of_speech": PartOfSpeech.NOUN,
            },
            {"lemma": "банан", "language": "ru", "part_of_speech": ""},  # default POS
            {
                "lemma": "FUCK OFF",
                "language": "en-GB",
                "part_of_speech": PartOfSpeech.COLLOCATION,
            },  # Assuming COLLOCATION POS
        ]
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == 201
        assert isinstance(response.data, list)
        assert len(response.data) == 3

        created_units_data = {
            (d["lemma"], d["language"], d["part_of_speech"], d["unit_type"])
            for d in response.data
        }

        expected_units_data = {
            (
                "apple tree",
                "en-GB",
                PartOfSpeech.NOUN,
                LexicalUnitType.COLLOC,
            ),  # Canonical lemma, COLLOC type
            ("банан", "ru", "", LexicalUnitType.SINGLE),  # Canonical lemma, SINGLE type
            (
                "fuck off",
                "en-GB",
                PartOfSpeech.COLLOCATION,
                LexicalUnitType.COLLOC,
            ),  # Canonical lemma, COLLOC type
        }
        assert created_units_data == expected_units_data
