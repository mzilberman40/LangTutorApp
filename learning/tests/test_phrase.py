# Пожалуйста, полностью замените содержимое этого файла.
import pytest
from django.db import IntegrityError
from learning.models import Phrase, ValidationStatus

pytestmark = pytest.mark.django_db


def test_phrase_uniqueness(phrase_factory):
    phrase_factory(text="Break a leg!", language="en")
    with pytest.raises(IntegrityError):
        phrase_factory(text="Break a leg!", language="en")


def test_phrase_string_representation(phrase_factory):
    phrase = phrase_factory(text="To be or not to be", language="en")
    assert "To be or not to be" in str(phrase)
    assert "[en]" in str(phrase)


def test_phrase_with_words(lexical_unit_factory, phrase_factory):
    lu1 = lexical_unit_factory(lemma="leg")
    phrase = phrase_factory(text="Break a leg")
    phrase.units.add(lu1)
    assert lu1 in phrase.units.all()


def test_phrase_defaults(phrase_factory):
    """Tests the default values for a new phrase."""
    phrase = phrase_factory()
    assert phrase.cefr is None
    assert phrase.category is None
    assert phrase.validation_status == ValidationStatus.UNVERIFIED
    assert phrase.validation_notes == ""
