import pytest
from learning.models import Phrase, PhraseTranslation
from learning.serializers import PhraseSerializer, PhraseTranslationSerializer

pytestmark = pytest.mark.django_db


def test_phrase_serializer_create_and_read():
    data = {"text": "Break a leg!", "language": "en", "category": "IDIOM", "cefr": "B2"}
    serializer = PhraseSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    phrase = serializer.save()

    assert phrase.text == "Break a leg!"
    assert phrase.language == "en"
    assert phrase.category == "IDIOM"
    assert phrase.cefr == "B2"

    serialized = PhraseSerializer(phrase).data
    assert serialized["text"] == "Break a leg!"
    assert serialized["language"] == "en"
    assert serialized["category"] == "IDIOM"
    assert serialized["cefr"] == "B2"


def test_phrase_translation_serializer_create_and_read():
    src = Phrase.objects.create(
        text="Break a leg!", language="en", category="IDIOM", cefr="B2"
    )
    tgt = Phrase.objects.create(
        text="Ни пуха ни пера!", language="ru", category="IDIOM", cefr="B2"
    )

    data = {
        "source_phrase": src.id,
        "target_phrase": tgt.id,
    }

    serializer = PhraseTranslationSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    trans = serializer.save()

    assert trans.source_phrase == src
    assert trans.target_phrase == tgt

    serialized = PhraseTranslationSerializer(trans).data
    assert serialized["source_phrase"] == src.id
    assert serialized["target_phrase"] == tgt.id
