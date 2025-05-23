import pytest
from django.db import IntegrityError
from learning.models import (
    Word,
    WordTranslation,
    Phrase,
    Lesson,
    LessonPhrase,
    LessonFile,
)

pytestmark = pytest.mark.django_db


def test_word_uniqueness():
    Word.objects.create(text="hello", language="en_GB")
    with pytest.raises(IntegrityError):
        Word.objects.create(text="hello", language="en_GB")


def test_word_translation_uniqueness():
    word = Word.objects.create(text="shine", language="en_GB")
    WordTranslation.objects.create(word=word, translation="сиять")
    with pytest.raises(IntegrityError):
        WordTranslation.objects.create(word=word, translation="сиять")


def test_phrase_cefr_choices():
    phrase = Phrase.objects.create(
        native_text="Спасибо!", target_text="Thank you!", cefr="A2", category="GENERAL"
    )
    assert phrase.cefr == "A2"


def test_lesson_phrase_order_unique():
    lesson = Lesson.objects.create(number=1)
    phrase1 = Phrase.objects.create(
        native_text="1", target_text="one", cefr="A1", category="GENERAL"
    )
    phrase2 = Phrase.objects.create(
        native_text="2", target_text="two", cefr="A1", category="GENERAL"
    )

    LessonPhrase.objects.create(lesson=lesson, phrase=phrase1, order=1)
    with pytest.raises(IntegrityError):
        LessonPhrase.objects.create(lesson=lesson, phrase=phrase2, order=1)


def test_lesson_file_uniqueness():
    lesson = Lesson.objects.create(number=2)
    file_path = "lessons/test1.mp3"
    LessonFile.objects.create(lesson=lesson, file_type="STUDY", file=file_path)

    with pytest.raises(IntegrityError):
        LessonFile.objects.create(
            lesson=lesson, file_type="STUDY", file="lessons/test1.mp3"
        )
