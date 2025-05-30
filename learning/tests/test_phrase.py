import pytest
from learning.models import Phrase, LexicalUnit

pytestmark = pytest.mark.django_db


def test_phrase_uniqueness():
    Phrase.objects.create(text="Break a leg!", language="en", category="IDIOM")
    with pytest.raises(Exception):
        Phrase.objects.create(text="Break a leg!", language="en")


def test_phrase_string_representation():
    phrase = Phrase.objects.create(
        text="To be or not to be", language="en", category="QUOTE"
    )
    assert "To be or not to be" in str(phrase)
    assert "[en]" in str(phrase)


def test_phrase_with_words():
    lu1 = LexicalUnit.objects.create(lemma="leg", language="en")
    phrase = Phrase.objects.create(text="Break a leg", language="en")
    phrase.units.add(lu1)
    assert lu1 in phrase.units.all()


def test_phrase_cefr_field():
    phrase = Phrase.objects.create(
        text="She has been studying English for three years.",
        language="en",
        category="GENERAL",
        cefr="B2",
    )
    assert phrase.cefr == "B2"
