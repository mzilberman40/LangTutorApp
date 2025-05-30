# learning/filters.py
import django_filters
from learning.models import Phrase, LexicalUnit, LexicalUnitTranslation


class PhraseFilter(django_filters.FilterSet):
    class Meta:
        model = Phrase
        fields = {
            "cefr": ["exact"],
            "language": ["exact"],
            "category": ["exact"],
            "units__lemma": ["exact", "icontains"],
        }


class LexicalUnitFilter(django_filters.FilterSet):
    class Meta:
        model = LexicalUnit
        fields = {
            "lemma": ["exact", "icontains"],
            "language": ["exact"],
            "status": ["exact"],
        }


class LexicalUnitTranslationFilter(django_filters.FilterSet):
    class Meta:
        model = LexicalUnitTranslation
        fields = {
            "source_unit__lemma": ["icontains"],
            "target_unit__lemma": ["icontains"],
            "translation_type": ["exact"],
            "confidence": ["gte", "lte"],
        }
