import pytest
from learning.models import Phrase, PhraseTranslation

pytestmark = pytest.mark.django_db


def test_phrase_translation_uniqueness():
    src = Phrase.objects.create(text="Break a leg!", language="en")
    tgt = Phrase.objects.create(text="Ни пуха ни пера!", language="ru")
    PhraseTranslation.objects.create(source_phrase=src, target_phrase=tgt)
    with pytest.raises(Exception):
        PhraseTranslation.objects.create(source_phrase=src, target_phrase=tgt)


def test_phrase_translation_str():
    src = Phrase.objects.create(text="Break a leg!", language="en")
    tgt = Phrase.objects.create(text="Удачи!", language="ru")
    t = PhraseTranslation.objects.create(
        source_phrase=src,
        target_phrase=tgt,
    )
    assert str(t) == "Break a leg! [en] → Удачи! [ru]"
