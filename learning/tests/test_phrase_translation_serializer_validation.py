import pytest
from learning.models import Phrase
from learning.serializers import PhraseTranslationSerializer

pytestmark = pytest.mark.django_db


def test_cannot_translate_phrase_to_itself():
    phrase = Phrase.objects.create(text="Good luck!", language="en", category="GENERAL")
    data = {
        "source_phrase": phrase.id,
        "target_phrase": phrase.id,
    }
    serializer = PhraseTranslationSerializer(data=data)
    assert not serializer.is_valid()
    assert "non_field_errors" in serializer.errors


def test_phrase_translation_valid_between_different_phrases():
    src = Phrase.objects.create(text="Good luck!", language="en", category="GENERAL")
    tgt = Phrase.objects.create(text="Удачи!", language="ru", category="GENERAL")
    data = {
        "source_phrase": src.id,
        "target_phrase": tgt.id,
    }
    serializer = PhraseTranslationSerializer(data=data)
    assert serializer.is_valid()


def test_phrase_translation_same_language_allowed():
    src = Phrase.objects.create(text="Cheers!", language="en", category="GENERAL")
    tgt = Phrase.objects.create(text="Thanks!", language="en", category="GENERAL")
    data = {
        "source_phrase": src.id,
        "target_phrase": tgt.id,
    }
    serializer = PhraseTranslationSerializer(data=data)
    assert serializer.is_valid()  # Same-language translation allowed (for now)
