# In learning/tests/test_enrichment_and_translation_tasks.py
import pytest
from unittest.mock import patch
from learning.models import LexicalUnit, LexicalUnitTranslation
from learning.enums import PartOfSpeech
from learning.tasks import enrich_details_async, translate_unit_async

pytestmark = pytest.mark.django_db


@patch("learning.tasks.get_lemma_details")
def test_enrich_resolves_to_multiple_variants_and_deletes_stub(
    mock_get_details, lexical_unit_factory
):
    stub_lu = lexical_unit_factory(lemma="record", language="en", part_of_speech="")
    mock_get_details.return_value = [
        {"part_of_speech": "noun", "pronunciation": "/ˈɹɛk.ɚd/"},
        {"part_of_speech": "verb", "pronunciation": "/ɹɪˈkɔɹd/"},
    ]

    # FIX: Pass the user's ID to the task call.
    enrich_details_async(unit_id=stub_lu.id, user_id=stub_lu.user.id)

    assert LexicalUnit.objects.filter(
        user=stub_lu.user, lemma="record", part_of_speech="noun"
    ).exists()
    assert LexicalUnit.objects.filter(
        user=stub_lu.user, lemma="record", part_of_speech="verb"
    ).exists()
    assert not LexicalUnit.objects.filter(pk=stub_lu.id).exists()


@patch("learning.tasks.translate_lemma_with_details")
def test_translate_creates_multiple_variants_and_links(
    mock_translate, lexical_unit_factory
):
    source_lu = lexical_unit_factory(lemma="fire", language="en", part_of_speech="noun")
    mock_translate.return_value = {
        "translated_lemma": "огонь",
        "translation_details": [
            {"part_of_speech": "noun", "pronunciation": "/ɐˈɡonʲ/"},
            {"part_of_speech": "verb", "pronunciation": "/ɐˈɡonʲitʲ/"},
        ],
    }

    # FIX: Pass the user's ID to the task call.
    translate_unit_async(
        unit_id=source_lu.id, user_id=source_lu.user.id, target_language_code="ru"
    )

    noun_translation = LexicalUnit.objects.get(
        user=source_lu.user, lemma="огонь", part_of_speech="noun"
    )
    verb_translation = LexicalUnit.objects.get(
        user=source_lu.user, lemma="огонь", part_of_speech="verb"
    )
    assert LexicalUnitTranslation.objects.filter(
        source_unit=source_lu, target_unit=noun_translation
    ).exists()
    assert LexicalUnitTranslation.objects.filter(
        source_unit=source_lu, target_unit=verb_translation
    ).exists()
