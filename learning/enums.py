from django.db import models


class PartOfSpeech(models.TextChoices):
    NOUN = "noun", "Noun"
    VERB = "verb", "Verb"
    ADJ = "adj", "Adjective"
    ADV = "adv", "Adverb"
    PRON = "pron", "Pronoun"
    PREP = "prep", "Preposition"
    CONJ = "conj", "Conjunction"
    INTERJ = "interj", "Interjection"
    NUM = "num", "Numeral"
    PART = "part", "Particle"


class CEFR(models.TextChoices):
    A1 = "A1", "A1"
    A2 = "A2", "A2"
    B1 = "B1", "B1"
    B2 = "B2", "B2"
    C1 = "C1", "C1"
    C2 = "C2", "C2"


class LexicalUnitStatus(models.TextChoices):
    LEARNING = "learning", "Learning"
    KNOWN = "known", "Known"
    TO_REVIEW = "to_review", "To Review"


class TranslationType(models.TextChoices):
    MANUAL = "manual", "Manual"
    AI = "ai", "AI"
    USER = "user", "User"
    IMPORTED = "imported", "Imported"


class PhraseCategory(models.TextChoices):
    GENERAL = "GENERAL", "General"
    IDIOM = "IDIOM", "Idiom"
    PROVERB = "PROVERB", "Proverb"
    QUOTE = "QUOTE", "Quote"


class LexicalCategory(models.TextChoices):
    SINGLE_WORD = "SINGLE_WORD", "Single Word"
    COLLOCATION = "COLLOCATION", "Collocation"
    PHRASAL_VERB = "PHRASAL_VERB", "Phrasal Verb"
    IDIOM = "IDIOM", "Idiom"
    # Можно расширить в будущем
    # PROVERB = "PROVERB", "Proverb"


class ValidationStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    VALID = "valid", "Valid"
    MISMATCH = "mismatch", "Mismatch"  # Несоответствие
    FAILED = "failed", "Failed"  # Ошибка при проверке
