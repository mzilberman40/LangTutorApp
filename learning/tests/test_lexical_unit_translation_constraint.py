# In learning/tests/test_lexical_unit_translation_constraint.py
import pytest
from rest_framework import status
from django.urls import reverse
from learning.enums import PartOfSpeech

pytestmark = pytest.mark.django_db


# The fixture now uses the lexical_unit_factory to create user-aware objects.
@pytest.fixture
def sample_units_for_constraint_tests(lexical_unit_factory):
    unit_en_apple = lexical_unit_factory(
        lemma="apple", language="en-GB", part_of_speech=PartOfSpeech.NOUN
    )
    unit_en_color = lexical_unit_factory(
        lemma="color", language="en-US", part_of_speech=PartOfSpeech.NOUN
    )
    unit_en_colour = lexical_unit_factory(
        lemma="colour", language="en-GB", part_of_speech=PartOfSpeech.NOUN
    )
    return {
        "en_apple": unit_en_apple,
        "en_color": unit_en_color,
        "en_colour": unit_en_colour,
    }


# The tests now require an authenticated client to make API calls.
def test_translation_cannot_be_to_itself_api(
    sample_units_for_constraint_tests, authenticated_client
):
    en_apple = sample_units_for_constraint_tests["en_apple"]
    url = reverse("lexicalunittranslation-list")
    payload = {"source_unit": en_apple.id, "target_unit": en_apple.id}

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot translate to itself" in str(response.data).lower()


def test_translation_between_same_primary_language_units_api(
    sample_units_for_constraint_tests, authenticated_client
):
    en_us_color = sample_units_for_constraint_tests["en_color"]
    en_gb_colour = sample_units_for_constraint_tests["en_colour"]
    url = reverse("lexicalunittranslation-list")
    payload = {"source_unit": en_us_color.id, "target_unit": en_gb_colour.id}

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "different languages" in str(response.data).lower()
