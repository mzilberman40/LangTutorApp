# In learning/tests/test_lexical_unit_translation_constraint.py
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from rest_framework import status
from learning.models import LexicalUnit
from learning.enums import PartOfSpeech  # Import your enum

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample_units_for_constraint_tests():
    # Using more descriptive names and ensuring POS is set
    unit_en_apple = LexicalUnit.objects.create(
        lemma="apple", language="en-GB", part_of_speech=PartOfSpeech.NOUN
    )
    unit_en_color = LexicalUnit.objects.create(
        lemma="color", language="en-US", part_of_speech=PartOfSpeech.NOUN
    )
    unit_en_colour = LexicalUnit.objects.create(
        lemma="colour", language="en-GB", part_of_speech=PartOfSpeech.NOUN
    )
    return {
        "en_apple": unit_en_apple,
        "en_color": unit_en_color,
        "en_colour": unit_en_colour,
    }


def test_translation_cannot_be_to_itself_api(sample_units_for_constraint_tests):
    # Renamed for clarity
    en_apple = sample_units_for_constraint_tests["en_apple"]
    client = APIClient()
    url = reverse("lexicalunittranslation-list")

    response = client.post(
        url,
        {
            "source_unit": en_apple.id,
            "target_unit": en_apple.id,
        },  # Translating to itself
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot translate to itself" in str(response.data).lower()


def test_translation_between_same_primary_language_units_api(
    sample_units_for_constraint_tests,
):
    # Renamed for clarity; this tests the serializer validation for different *primary* languages
    # Your LexicalUnitTranslationSerializer has this check:
    # if self._primary_lang(src.language) == self._primary_lang(tgt.language):
    #     raise serializers.ValidationError("Source and target units must be in different languages.")

    en_us_color = sample_units_for_constraint_tests["en_color"]  # en-US
    en_gb_colour = sample_units_for_constraint_tests["en_colour"]  # en-GB

    client = APIClient()
    url = reverse("lexicalunittranslation-list")

    response = client.post(
        url,
        {
            "source_unit": en_us_color.id,
            "target_unit": en_gb_colour.id,
        },  # Both 'en' primary
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "different languages" in str(response.data).lower()
