from rest_framework import serializers

from learning.enums import CEFR
from learning.models import (
    LexicalUnit,
    LexicalUnitTranslation,
    TranslationType,
    Phrase,
    PhraseTranslation,
    LexicalUnitType,
)
from learning.validators import bcp47_validator


class LexicalUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = LexicalUnit
        fields = "__all__"

    def validate(self, data):
        lemma = data.get("lemma", "")
        if " " in lemma:
            data["unit_type"] = LexicalUnitType.COLLOC
        else:
            data["unit_type"] = LexicalUnitType.SINGLE
        return data


class LexicalUnitTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LexicalUnitTranslation
        fields = "__all__"

    def _primary_lang(self, code: str) -> str:
        """Return the primary sub-tag of a BCP-47 code (e.g. 'en' from 'en-GB')."""
        return code.split("-")[0].lower()

    def validate(self, data):
        src = data["source_unit"]
        tgt = data["target_unit"]

        # ❶ self-translation
        if src == tgt:
            raise serializers.ValidationError("A unit cannot translate to itself.")

        # ❷ same primary language
        if self._primary_lang(src.language) == self._primary_lang(tgt.language):
            raise serializers.ValidationError(
                "Source and target units must be in different languages."
            )

        return data


# Used only for nested input in unitTranslationBulkSerializer — do not use this in standard API views.
class LexicalUnitInputSerializer(serializers.Serializer):
    lemma = serializers.CharField()
    language = serializers.CharField()
    part_of_speech = serializers.CharField(required=False)
    pronunciation = serializers.CharField()


class LexicalUnitTranslationBulkSerializer(serializers.Serializer):
    source_unit = (
        LexicalUnitInputSerializer()
    )  # Nested input, validated but not saved via ModelSerializer
    targets = LexicalUnitInputSerializer(many=True)  # List of nested input entries
    translation_type = serializers.ChoiceField(
        choices=[c[0] for c in TranslationType.choices], default="manual"
    )
    confidence = serializers.FloatField(required=False)

    def _primary_lang(self, code: str) -> str:
        return code.split("-")[0].lower()

    def validate(self, data):
        src_lang = self._primary_lang(data["source_unit"]["language"])
        for target in data["targets"]:
            tgt_lang = self._primary_lang(target["language"])
            if src_lang == tgt_lang:
                raise serializers.ValidationError(
                    "Source and target languages must differ."
                )
            if (
                data["source_unit"]["lemma"].strip().lower()
                == target["lemma"].strip().lower()
                and data["source_unit"]["language"] == target["language"]
            ):
                raise serializers.ValidationError(
                    "A unit cannot translate to itself in the same language."
                )
        return data

    def create(self, validated_data):
        source_data = validated_data["source_unit"]
        targets_data = validated_data["targets"]
        translation_type = validated_data.get("translation_type", "manual")
        confidence = validated_data.get("confidence")

        if confidence is None and translation_type == "ai":
            confidence = 0.8

        source_unit, _ = LexicalUnit.objects.get_or_create(
            lemma=source_data["lemma"],
            language=source_data["language"],
            defaults={
                "part_of_speech": source_data.get("part_of_speech"),
                "pronunciation": source_data["pronunciation"],
            },
        )

        created_translations = []
        for target in targets_data:
            target_unit, _ = LexicalUnit.objects.get_or_create(
                lemma=target["lemma"],
                language=target["language"],
                defaults={
                    "part_of_speech": target.get("part_of_speech"),
                    "pronunciation": target["pronunciation"],
                },
            )
            wt = LexicalUnitTranslation.objects.create(
                source_unit=source_unit,
                target_unit=target_unit,
                translation_type=translation_type,
                confidence=confidence,
            )
            created_translations.append(wt)

        return created_translations


class PhraseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phrase
        fields = ["id", "text", "language", "category", "units", "cefr"]


class PhraseTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhraseTranslation
        fields = ["id", "source_phrase", "target_phrase"]

    def validate(self, data):
        if data["source_phrase"] == data["target_phrase"]:
            raise serializers.ValidationError("A phrase cannot translate to itself.")
        return data


class PhraseGenerationRequestSerializer(serializers.Serializer):
    target_translation_language = serializers.CharField(
        max_length=16,  # Or a suitable length for BCP47 codes
        validators=[bcp47_validator],  # <--- APPLY THE VALIDATOR HERE
    )
    cefr_level = serializers.ChoiceField(choices=CEFR.choices)


class EnrichLexicalUnitRequestSerializer(serializers.Serializer):
    target_translation_languages = serializers.ListField(
        child=serializers.CharField(max_length=32, validators=[bcp47_validator]),
        required=False,  # Making translation optional
        help_text="Optional list of BCP47 language codes to translate the lexical unit into.",
    )
    force_update_details = serializers.BooleanField(
        default=False,
        required=False,
        help_text="If true, attempt to fetch and update details (POS, pronunciation) even if they already exist.",
    )
