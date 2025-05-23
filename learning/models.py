from django.db import models


class Word(models.Model):
    """Studied word (usually in the target language)."""

    text = models.CharField(max_length=100)
    language = models.CharField(max_length=20, default="en_GB")  # Studied language

    class Meta:
        unique_together = ("text", "language")
        indexes = [
            models.Index(fields=["text"]),
        ]

    def __str__(self):
        return f"{self.text} [{self.language}]"


class WordTranslation(models.Model):
    """Native-language translation(s) of a studied word."""

    word = models.ForeignKey(
        Word, on_delete=models.CASCADE, related_name="translations"
    )
    translation = models.CharField(max_length=100)
    note = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = ("word", "translation")

    def __str__(self):
        return f"{self.word.text} ↔ {self.translation}"


class Phrase(models.Model):
    CEFR_CHOICES = [
        ("A1", "A1"),
        ("A2", "A2"),
        ("B1", "B1"),
        ("B2", "B2"),
        ("C1", "C1"),
        ("C2", "C2"),
    ]

    CATEGORY_CHOICES = [
        ("GENERAL", "General"),
        ("IDIOM", "Idiom"),
        ("PROVERB", "Proverb"),
        ("QUOTE", "Quote"),
    ]

    native_text = models.TextField()  # in the learner's native language
    target_text = models.TextField()  # in the studied (target) language
    cefr = models.CharField(max_length=2, choices=CEFR_CHOICES)
    category = models.CharField(
        max_length=10, choices=CATEGORY_CHOICES, default="GENERAL"
    )
    words = models.ManyToManyField(Word, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["cefr"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.native_text} — {self.target_text}"


class Lesson(models.Model):
    number = models.PositiveIntegerField(unique=True)
    phrases = models.ManyToManyField(Phrase, through="LessonPhrase")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lesson {self.number}"


class LessonPhrase(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    phrase = models.ForeignKey(Phrase, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        unique_together = ("lesson", "order")


class LessonFile(models.Model):
    FILE_TYPE_CHOICES = [
        ("TXT", "Text"),
        ("STUDY", "Study MP3"),
        ("TRAINING", "Training MP3"),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="files")
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    file = models.FileField(upload_to="lessons/", unique=True)

    class Meta:
        unique_together = ("lesson", "file_type")

    def __str__(self):
        return f"{self.lesson} [{self.file_type}]"
