# learning/serializers/phrases.py
from rest_framework import serializers

from .base import LanguageField
from ..models import Phrase, PhraseTranslation


class PhraseSerializer(serializers.ModelSerializer):
    language = LanguageField()
    validation_status = serializers.CharField(read_only=True)
    validation_notes = serializers.CharField(read_only=True)

    class Meta:
        model = Phrase
        fields = [
            "id",
            "text",
            "language",
            "category",
            "units",
            "cefr",
            "validation_status",
            "validation_notes",
        ]


class PhraseTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhraseTranslation
        fields = ["id", "source_phrase", "target_phrase"]

    def validate(self, data):
        if data["source_phrase"] == data["target_phrase"]:
            raise serializers.ValidationError("A phrase cannot translate to itself.")
        return data