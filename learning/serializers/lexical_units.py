# learning/serializers/lexical_units.py
from rest_framework import serializers

from .base import LanguageField
from ..enums import LexicalCategory, PartOfSpeech, TranslationType
from ..models import LexicalUnit, LexicalUnitTranslation
from ..utils import get_canonical_lemma


class LexicalUnitSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    language = LanguageField()

    class Meta:
        model = LexicalUnit
        fields = [
            "id",
            "user",
            "lemma",
            "lexical_category",
            "language",
            "status",
            "notes",
            "date_added",
            "last_reviewed",
            "part_of_speech",
            "pronunciation",
            "validation_status",
            "validation_notes",
        ]
        read_only_fields = (
            "date_added",
            "last_reviewed",
            "user",
            "validation_status",
            "validation_notes",
        )

    def validate_lemma(self, value):
        return get_canonical_lemma(value)

    def validate(self, data):
        """Custom validation to check for uniqueness before hitting the database."""
        if not self.instance:  # Only on create
            request = self.context.get("request")
            if request and hasattr(request, "user"):
                query_params = {
                    "user": request.user,
                    "lemma": data.get("lemma"),
                    "language": data.get("language"),
                    "part_of_speech": data.get("part_of_speech"),
                    "lexical_category": data.get("lexical_category"),
                }
                if LexicalUnit.objects.filter(**query_params).exists():
                    raise serializers.ValidationError(
                        "This lexical unit already exists in your list."
                    )
        return data


class LexicalUnitInputSerializer(serializers.Serializer):
    """Validates the structure of individual lexical unit data for bulk operations."""

    lemma = serializers.CharField(max_length=100)
    language = LanguageField()
    lexical_category = serializers.ChoiceField(choices=LexicalCategory.choices)
    part_of_speech = serializers.ChoiceField(choices=PartOfSpeech.choices)
    pronunciation = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )


class LexicalUnitTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LexicalUnitTranslation
        fields = [
            "id",
            "source_unit",
            "target_unit",
            "translation_type",
            "confidence",
            "validation_status",
            "validation_notes",
        ]
        read_only_fields = ("validation_status", "validation_notes")

    def _primary_lang(self, code: str) -> str:
        return code.split("-")[0].lower()

    def validate(self, data):
        src, tgt = data["source_unit"], data["target_unit"]
        if src == tgt:
            raise serializers.ValidationError("A unit cannot translate to itself.")
        if self._primary_lang(src.language) == self._primary_lang(tgt.language):
            raise serializers.ValidationError(
                "Source and target units must be in different languages."
            )
        if src.user != tgt.user:
            raise serializers.ValidationError(
                "Source and target units must belong to the same user."
            )
        request = self.context.get("request")
        if not request or not hasattr(request, "user") or src.user != request.user:
            raise serializers.ValidationError(
                "You can only create translations for your own lexical units."
            )
        return data


class LexicalUnitTranslationBulkSerializer(serializers.Serializer):
    source_unit = LexicalUnitInputSerializer()
    targets = LexicalUnitInputSerializer(many=True, min_length=1)
    translation_type = serializers.ChoiceField(
        choices=TranslationType.choices, default=TranslationType.MANUAL
    )
    confidence = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)

    def validate_source_unit(self, data):
        data["lemma"] = get_canonical_lemma(data["lemma"])
        return data

    def validate_targets(self, data):
        for target in data:
            target["lemma"] = get_canonical_lemma(target["lemma"])
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        if not request or not hasattr(request, "user"):
            raise serializers.ValidationError("Request context with user is required.")
        user = request.user
        source_data = validated_data["source_unit"]
        targets_data = validated_data["targets"]
        translation_type = validated_data.get(
            "translation_type", TranslationType.MANUAL
        )

        source_unit, _ = LexicalUnit.objects.get_or_create(
            user=user,
            lemma=source_data["lemma"],
            language=source_data["language"],
            lexical_category=source_data["lexical_category"],
            part_of_speech=source_data["part_of_speech"],
            defaults={"pronunciation": source_data.get("pronunciation", "")},
        )
        created_translations = []
        for target_data in targets_data:
            target_unit, _ = LexicalUnit.objects.get_or_create(
                user=user,
                lemma=target_data["lemma"],
                language=target_data["language"],
                lexical_category=target_data["lexical_category"],
                part_of_speech=target_data["part_of_speech"],
                defaults={"pronunciation": target_data.get("pronunciation", "")},
            )
            translation, _ = LexicalUnitTranslation.objects.get_or_create(
                source_unit=source_unit,
                target_unit=target_unit,
                defaults={"translation_type": translation_type},
            )
            created_translations.append(translation)
        return created_translations