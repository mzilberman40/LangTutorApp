from django.contrib.auth.models import User
from django.db import models

from learning.enums import (
    LexicalUnitStatus,
    PartOfSpeech,
    TranslationType,
    CEFR,
    ValidationStatus,
    LexicalCategory,
    PhraseCategory,
)
from learning.utils import get_canonical_lemma
from learning.validators import bcp47_validator, supported_language_validator


class LexicalUnit(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lexical_units"
    )

    lemma = models.CharField(max_length=100)
    lexical_category = models.CharField(
        max_length=50,
        choices=LexicalCategory.choices,
        default=LexicalCategory.SINGLE_WORD,
        help_text="The structural type of the lexical unit (e.g., single word, idiom).",
    )
    language = models.CharField(
        max_length=16,
        # default="en-GB",
        validators=[bcp47_validator, supported_language_validator],
        help_text="BCP47 language code (e.g. en, en-GB, he-IL)",
    )
    status = models.CharField(
        max_length=10,
        choices=LexicalUnitStatus.choices,
        default=LexicalUnitStatus.LEARNING,
        help_text="Learning status of the lexical unit",
    )
    notes = models.TextField(
        blank=True, default="", help_text="Personal notes about the lexical unit"
    )
    date_added = models.DateTimeField(auto_now_add=True)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    part_of_speech = models.CharField(
        max_length=32,
        choices=PartOfSpeech.choices,
        help_text="Part of speech",
    )
    pronunciation = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Phonetic transcription or IPA",
    )

    validation_status = models.CharField(
        max_length=10,
        choices=ValidationStatus.choices,
        default=ValidationStatus.UNVERIFIED,
        help_text="The status of the background validation check.",
    )

    validation_notes = models.TextField(
        blank=True,
        default="",
        help_text="Notes from the validation process, e.g., suggested corrections.",
    )

    class Meta:
        unique_together = (
            "user",
            "lemma",
            "language",
            "part_of_speech",
            "lexical_category",
        )
        indexes = [
            models.Index(fields=["lemma"]),
            models.Index(fields=["language"]),
            models.Index(fields=["part_of_speech"]),
            models.Index(fields=["lexical_category"]),
        ]

    def save(self, *args, **kwargs):
        # Логика определения unit_type по пробелу удаляется.
        self.lemma = get_canonical_lemma(self.lemma)
        super().save(*args, **kwargs)

    def __str__(self):
        # __str__ метод остается таким же, как в прошлой рекомендации.
        details = f"({self.get_lexical_category_display()}, {self.get_part_of_speech_display()})"
        username = (
            self.user.username if hasattr(self, "user") and self.user else "No-User"
        )
        return f"{self.lemma} {details} [{self.language}] ({username})"


class LexicalUnitTranslation(models.Model):
    source_unit = models.ForeignKey(
        "LexicalUnit", related_name="translations_from", on_delete=models.CASCADE
    )
    target_unit = models.ForeignKey(
        "LexicalUnit", related_name="translations_to", on_delete=models.CASCADE
    )
    translation_type = models.CharField(
        max_length=10,
        choices=TranslationType.choices,
        default=TranslationType.MANUAL,
        help_text="How this translation was added",
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="How confident the system is about this translation (0–1)",
    )

    validation_status = models.CharField(
        max_length=10,
        choices=ValidationStatus.choices,  # Используем тот же Enum
        default=ValidationStatus.UNVERIFIED,
    )
    validation_notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("source_unit", "target_unit")
        # NOTE: SQLite does not support this constraint, use only for PostgreSQL in production
        # constraints = [
        #     CheckConstraint(
        #         check=~Q(source_unit=F("target_unit")),
        #         name="no_self_translation_unit",
        #     )
        # ]

    def __str__(self):
        return f"{str(self.source_unit)} → {str(self.target_unit)}"  # <--- MODIFIED


class Phrase(models.Model):
    text = models.TextField()
    language = models.CharField(
        max_length=16,
        validators=[bcp47_validator, supported_language_validator],
        help_text="BCP47 language code (e.g. en, ru, he-IL)",
    )
    cefr = models.CharField(max_length=2, choices=CEFR.choices, blank=True, null=True)
    category = models.CharField(
        max_length=10, choices=PhraseCategory.choices, blank=True, null=True
    )
    units = models.ManyToManyField(LexicalUnit, blank=True)

    # +++ Новые поля для валидации +++
    validation_status = models.CharField(
        max_length=10,
        choices=ValidationStatus.choices,
        default=ValidationStatus.UNVERIFIED,
    )
    validation_notes = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("text", "language")
        indexes = [
            models.Index(fields=["language"]),
            models.Index(fields=["category"]),
            models.Index(fields=["cefr"]),
        ]

    def __str__(self):
        return f"{self.text} [{self.language}]"


class PhraseTranslation(models.Model):
    source_phrase = models.ForeignKey(
        Phrase, related_name="translations_from", on_delete=models.CASCADE
    )
    target_phrase = models.ForeignKey(
        Phrase, related_name="translations_to", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("source_phrase", "target_phrase")
        # NOTE: SQLite does not support this constraint, use only for PostgreSQL in production
        # constraints = [
        #     CheckConstraint(
        #         check=~Q(source_phrase=F("target_phrase")),
        #         name="no_self_translation_phrase",
        #     )
        # ]
        # indexes = [
        # models.Index(fields=["cefr"]),
        # ]

    def __str__(self):
        return f"{self.source_phrase.text} [{self.source_phrase.language}] → {self.target_phrase.text} [{self.target_phrase.language}]"


# class Lesson(models.Model):
#     number = models.PositiveIntegerField(unique=True)
#     phrases = models.ManyToManyField(Phrase, through="LessonPhrase")
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return f"Lesson {self.number}"
#
# class LessonPhrase(models.Model):
#     lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
#     phrase = models.ForeignKey(Phrase, on_delete=models.CASCADE)
#     order = models.PositiveIntegerField()
#
#     class Meta:
#         unique_together = ("lesson", "order")
#
# class LessonFile(models.Model):
#     FILE_TYPE_CHOICES = [
#         ("TXT", "Text"),
#         ("STUDY", "Study MP3"),
#         ("TRAINING", "Training MP3"),
#     ]
#     lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="files")
#     file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
#     file = models.FileField(upload_to="lessons/", unique=True)
#
#     class Meta:
#         unique_together = ("lesson", "file_type")
#
#     def __str__(self):
#         return f"{self.lesson} [{self.file_type}]"
