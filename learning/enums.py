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
    COLLOCATION = "collocation", "Collocation"  # <-- New addition
    PHRASAL_VERB = "phrasal_verb", "Phrasal Verb"
    IDIOM = "idiom", "Idiom"
    OTHER_MWU = "multi_word_unit", "Multi-Word Unit"  # A very generic fallback


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


class LexicalUnitType(models.TextChoices):
    SINGLE = "single", "Single word"
    COLLOC = "colloc", "Collocation / phrasal verb"
