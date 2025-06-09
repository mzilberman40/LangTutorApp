from django.contrib.auth.models import User
from django.db import models

from learning.enums import (
    LexicalUnitType,
    LexicalUnitStatus,
    PartOfSpeech,
    TranslationType,
    PhraseCategory,
    CEFR,
)
from learning.utils import get_canonical_lemma
from learning.validators import bcp47_validator


class LexicalUnit(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lexical_units"
    )

    lemma = models.CharField(max_length=100)
    unit_type = models.CharField(
        max_length=6,
        choices=LexicalUnitType.choices,
        default=LexicalUnitType.SINGLE,
        help_text="‘single’ = one token; ‘colloc’ = multi-word item",
    )
    language = models.CharField(
        max_length=16,
        # default="en-GB",
        validators=[bcp47_validator],
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

    class Meta:
        unique_together = ("user", "lemma", "language", "part_of_speech")
        indexes = [
            models.Index(fields=["lemma"]),
            models.Index(fields=["language"]),
            models.Index(fields=["part_of_speech"]),
        ]

    def save(self, *args, **kwargs):
        # Use the utility function for canonicalization
        self.lemma = get_canonical_lemma(self.lemma)

        # Set unit_type based on the now definitively canonical lemma
        if self.lemma and " " in self.lemma:
            self.unit_type = LexicalUnitType.COLLOC
        else:
            self.unit_type = LexicalUnitType.SINGLE

        super().save(*args, **kwargs)

    def __str__(self):
        # The new, user-aware __str__ method
        details = ""
        if self.part_of_speech:
            details += f"({self.part_of_speech}) "

        # Safely get username, self.user might not be loaded
        username = (
            self.user.username if hasattr(self, "user") and self.user else "No-User"
        )
        return f"{self.lemma} {details}[{self.language}] ({username})"


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
        validators=[bcp47_validator],
        help_text="BCP47 language code (e.g. en, ru, he-IL)",
    )
    cefr = models.CharField(max_length=2, choices=CEFR.choices)

    category = models.CharField(
        max_length=10, choices=PhraseCategory.choices, default=PhraseCategory.GENERAL
    )
    units = models.ManyToManyField(LexicalUnit, blank=True)

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
