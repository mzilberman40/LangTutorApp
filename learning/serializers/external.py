# learning/serializers/external.py
from django.db import transaction
from rest_framework import serializers

from .lexical_units import LexicalUnitSerializer
from .phrases import PhraseSerializer
from ..enums import LexicalCategory, PartOfSpeech, TranslationType
from ..models import LexicalUnit, LexicalUnitTranslation, Phrase, PhraseTranslation
from ..utils import get_canonical_lemma


class ExternalTextPayloadSerializer(serializers.Serializer):
    """Serializes a single text payload object from an external service."""

    text = serializers.CharField(max_length=1000)
    language = serializers.CharField(max_length=10)
    part_of_speech = serializers.ChoiceField(
        choices=PartOfSpeech.choices, required=False
    )
    lexical_category = serializers.ChoiceField(
        choices=LexicalCategory.choices, required=False
    )
    pronunciation = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )


class ExternalImportSerializer(serializers.Serializer):
    """
    Main serializer for handling incoming data from an external service.
    Routes data to either LexicalUnit or Phrase based on 'entity_type'.
    """

    ENTITY_CHOICES = (("LEXICAL_UNIT", "Lexical Unit"), ("PHRASE", "Phrase"))
    entity_type = serializers.ChoiceField(choices=ENTITY_CHOICES)
    source = ExternalTextPayloadSerializer()
    targets = ExternalTextPayloadSerializer(many=True)
    confidence = serializers.FloatField(required=False)

    def validate_source(self, data):
        """Validate source based on entity type."""
        if self.initial_data.get("entity_type") == "LEXICAL_UNIT":
            if not data.get("part_of_speech") or not data.get("lexical_category"):
                raise serializers.ValidationError(
                    "'part_of_speech' and 'lexical_category' are required for a LEXICAL_UNIT."
                )
        return data

    @transaction.atomic
    def create(self, validated_data):
        entity_type = validated_data["entity_type"]
        if entity_type == "LEXICAL_UNIT":
            return self._create_lexical_unit(validated_data)
        elif entity_type == "PHRASE":
            return self._create_phrase(validated_data)

    def _create_lexical_unit(self, validated_data):
        request = self.context.get("request")
        user = self.context.get("user", request.user) # Use injected user if available
        source_data = validated_data["source"]

        source_unit, _ = LexicalUnit.objects.get_or_create(
            user=user,
            lemma=get_canonical_lemma(source_data["text"]),
            language=source_data["language"],
            part_of_speech=source_data["part_of_speech"],
            lexical_category=source_data["lexical_category"],
            defaults={"pronunciation": source_data.get("pronunciation", "")},
        )

        created_target_units = []
        for target_data in validated_data["targets"]:
            target_unit, _ = LexicalUnit.objects.get_or_create(
                user=user,
                lemma=get_canonical_lemma(target_data["text"]),
                language=target_data["language"],
                part_of_speech=target_data["part_of_speech"],
                lexical_category=target_data["lexical_category"],
                defaults={"pronunciation": target_data.get("pronunciation", "")},
            )
            created_target_units.append(target_unit)
            LexicalUnitTranslation.objects.get_or_create(
                source_unit=source_unit,
                target_unit=target_unit,
                defaults={
                    "translation_type": validated_data.get(
                        "translation_type", TranslationType.IMPORTED
                    ),
                    "confidence": validated_data.get("confidence"),
                },
            )

        return {
            "created_entity": "LexicalUnit",
            "source": LexicalUnitSerializer(source_unit).data,
            "targets": LexicalUnitSerializer(created_target_units, many=True).data,
        }

    def _create_phrase(self, validated_data):
        source_data = validated_data["source"]
        source_phrase, _ = Phrase.objects.get_or_create(
            text=source_data["text"], language=source_data["language"]
        )

        created_target_phrases = []
        for target_data in validated_data["targets"]:
            target_phrase, _ = Phrase.objects.get_or_create(
                text=target_data["text"], language=target_data["language"]
            )
            created_target_phrases.append(target_phrase)
            PhraseTranslation.objects.get_or_create(
                source_phrase=source_phrase, target_phrase=target_phrase
            )

        return {
            "created_entity": "Phrase",
            "source": PhraseSerializer(source_phrase).data,
            "targets": PhraseSerializer(created_target_phrases, many=True).data,
        }