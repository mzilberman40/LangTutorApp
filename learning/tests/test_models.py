import pytest
from django.db import IntegrityError
from learning.models import (
    LexicalUnit,
    LexicalUnitTranslation,
    # Lesson,
    # LessonPhrase,
    # LessonFile,
)

pytestmark = pytest.mark.django_db

# --- Lexical Unit Model Tests ---


def test_lexical_unit_uniqueness():
    LexicalUnit.objects.create(lemma="hello", language="en-GB")
    with pytest.raises(IntegrityError):
        LexicalUnit.objects.create(lemma="hello", language="en-GB")


def test_lexical_unit_blank_notes_and_status_defaults():
    w = LexicalUnit.objects.create(lemma="melon", language="en-GB")
    assert w.status == "learning"
    assert w.notes == ""
    assert w.lemma == "melon"


def test_lexical_unit_two_words():
    w = LexicalUnit.objects.create(lemma="take off", language="en-GB")
    assert w.status == "learning"
    assert w.notes == ""
    assert w.lemma == "take off"


def test_lexical_unit_repr_and_fields():
    w = LexicalUnit.objects.create(
        lemma="carrot", language="en-GB", notes="vegetable", status="known"
    )
    assert "carrot" in str(w)
    assert "[en-GB]" in str(w)
    assert w.notes == "vegetable"
    assert w.status == "known"


# --- WordTranslation Model Tests ---


def test_lexical_unit_translation_unique():
    w1 = LexicalUnit.objects.create(lemma="apple", language="en-GB")
    w2 = LexicalUnit.objects.create(lemma="яблоко", language="ru")
    LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)
    with pytest.raises(IntegrityError):
        LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)


def test_lexical_unit_translation_str():
    w1 = LexicalUnit.objects.create(lemma="cat", language="en-GB")
    w2 = LexicalUnit.objects.create(lemma="кот", language="ru")
    trans = LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)
    assert str(trans) == "cat → кот"


def test_word_translation_str_and_fields():
    w1 = LexicalUnit.objects.create(lemma="river", language="en-GB")
    w2 = LexicalUnit.objects.create(lemma="река", language="ru")
    t = LexicalUnitTranslation.objects.create(
        source_unit=w1, target_unit=w2, translation_type="manual", confidence=0.75
    )
    assert str(t) == "river → река"
    assert t.translation_type == "manual"
    assert t.confidence == 0.75


def test_word_translation_reverse_direction_allowed():
    w1 = LexicalUnit.objects.create(lemma="pen", language="en-GB")
    w2 = LexicalUnit.objects.create(lemma="ручка", language="ru")
    t1 = LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)
    # Reverse translation should be allowed (not considered duplicate)
    t2 = LexicalUnitTranslation.objects.create(source_unit=w2, target_unit=w1)
    assert t1.source_unit == w1
    assert t2.source_unit == w2
    assert t1 != t2


#
# def test_lesson_phrase_order_unique():
#     lesson = Lesson.objects.create(number=1)
#     phrase1 = Phrase.objects.create(
#         native_text="1", target_text="one", cefr="A1", category="GENERAL"
#     )
#     phrase2 = Phrase.objects.create(
#         native_text="2", target_text="two", cefr="A1", category="GENERAL"
#     )
#
#     LessonPhrase.objects.create(lesson=lesson, phrase=phrase1, order=1)
#     with pytest.raises(IntegrityError):
#         LessonPhrase.objects.create(lesson=lesson, phrase=phrase2, order=1)
#
#
# def test_lesson_file_uniqueness():
#     lesson = Lesson.objects.create(number=2)
#     file_path = "lessons/test1.mp3"
#     LessonFile.objects.create(lesson=lesson, file_type="STUDY", file=file_path)
#
#     with pytest.raises(IntegrityError):
#         LessonFile.objects.create(
#             lesson=lesson, file_type="STUDY", file="lessons/test1.mp3"
#         )
