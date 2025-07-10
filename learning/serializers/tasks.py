# learning/serializers/tasks.py
from rest_framework import serializers

from .base import LanguageField
from ..enums import CEFR, PartOfSpeech


class ResolveLemmaRequestSerializer(serializers.Serializer):
    """Validates the input for the lemma resolution/creation endpoint."""

    lemma = serializers.CharField(max_length=100)
    language = LanguageField()
    part_of_speech = serializers.ChoiceField(
        choices=PartOfSpeech.choices, required=False
    )
    pronunciation = serializers.CharField(max_length=100, required=False)


class ResolvedLemmaVariantSerializer(serializers.Serializer):
    """Represents a single structural/POS variant returned by the LLM."""

    lexical_category = serializers.CharField()
    part_of_speech = serializers.CharField()
    pronunciation = serializers.CharField(allow_blank=True, allow_null=True)


class ResolvedLemmaResponseSerializer(serializers.Serializer):
    """Represents the full response when a lemma is resolved into multiple variants."""

    lemma = serializers.CharField()
    language = serializers.CharField()
    variants = ResolvedLemmaVariantSerializer(many=True)
    exists = serializers.BooleanField()


class PhraseGenerationRequestSerializer(serializers.Serializer):
    target_language = LanguageField()
    cefr = serializers.ChoiceField(choices=CEFR.choices)


class EnrichDetailsRequestSerializer(serializers.Serializer):
    """Validates the request for the detail enrichment endpoint."""

    force_update = serializers.BooleanField(default=False, required=False)


class TranslateRequestSerializer(serializers.Serializer):
    """Validates the request for the translation endpoint."""

    target_language_code = LanguageField()


class AnalyzeTextRequestSerializer(serializers.Serializer):
    """
    Serializes the request data for analyzing a text block.
    """

    text = serializers.CharField()