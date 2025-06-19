from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from learning.enums import CEFR, PartOfSpeech, LexicalCategory
from learning.models import (
    LexicalUnit,
    LexicalUnitTranslation,
    TranslationType,
    Phrase,
    PhraseTranslation,
)
from learning.utils import get_canonical_lemma
from learning.validators import bcp47_validator, supported_language_validator


class ResolveLemmaRequestSerializer(serializers.Serializer):
    """Validates the input for the lemma resolution/creation endpoint."""

    lemma = serializers.CharField(max_length=100)
    language = serializers.CharField(
        max_length=16, validators=[bcp47_validator, supported_language_validator]
    )
    part_of_speech = serializers.ChoiceField(
        choices=PartOfSpeech.choices,
        required=False,  # This field is optional in the request
    )
    # You could add pronunciation here as another optional field
    pronunciation = serializers.CharField(max_length=100, required=False)


class ResolvedLemmaVariantSerializer(serializers.Serializer):
    """Represents a single structural/POS variant returned by the LLM."""

    lexical_category = serializers.CharField()  # <-- Добавили
    part_of_speech = serializers.CharField()
    pronunciation = serializers.CharField(allow_blank=True, allow_null=True)


class ResolvedLemmaResponseSerializer(serializers.Serializer):
    """Represents the full response when a lemma is resolved into multiple variants."""

    lemma = serializers.CharField()
    language = serializers.CharField()
    variants = ResolvedLemmaVariantSerializer(many=True)
    exists = serializers.BooleanField()


class LexicalUnitSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    # Поле unit_type полностью удалено
    language = serializers.CharField(
        max_length=16, validators=[bcp47_validator, supported_language_validator]
    )
    # +++ Добавляем новое поле. Делаем его read_only, т.к. оно будет вычисляться сервисами, а не задаваться клиентом напрямую.
    lexical_category = serializers.CharField(read_only=True)

    class Meta:
        model = LexicalUnit
        fields = [
            "id",
            "user",
            "lemma",
            "lexical_category",  # <-- Добавили
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
            "lexical_category",  # <-- Добавили в read_only
        )

    def validate(self, data):
        """
        Manually enforce user-scoped uniqueness on creation.
        """
        # On a POST (create) request, self.instance is None.
        if not self.instance:
            request = self.context.get("request")
            if request and hasattr(request, "user"):
                # Combine the necessary fields for the uniqueness check
                check_kwargs = {
                    "user": request.user,
                    "lemma": data.get("lemma"),
                    "language": data.get("language"),
                    "part_of_speech": data.get("part_of_speech"),
                }
                if LexicalUnit.objects.filter(**check_kwargs).exists():
                    raise serializers.ValidationError(
                        "This lexical unit already exists in your list."
                    )
        return data

    def validate_lemma(self, value):
        from .utils import get_canonical_lemma

        return get_canonical_lemma(value)


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
        """Return the primary sub-tag of a BCP-47 code (e.g. 'en' from 'en-GB')."""
        return code.split("-")[0].lower()

    def validate(self, data):
        src = data["source_unit"]
        tgt = data["target_unit"]

        # ❶ Проверка на само-перевод
        if src == tgt:
            raise serializers.ValidationError("A unit cannot translate to itself.")

        # ❷ Проверка на разные языки
        if self._primary_lang(src.language) == self._primary_lang(tgt.language):
            raise serializers.ValidationError(
                "Source and target units must be in different languages."
            )

        # ❸ Проверка, что обе единицы принадлежат одному и тому же пользователю
        if src.user != tgt.user:
            raise serializers.ValidationError(
                "Source and target units must belong to the same user."
            )

        # ❹ Проверка, что текущий пользователь является владельцем этих единиц
        request = self.context.get("request")
        if not request or not hasattr(request, "user"):
            # Эта проверка на случай, если сериализатор используется вне контекста запроса
            raise serializers.ValidationError("Request context with user is required.")

        if src.user != request.user:
            raise serializers.ValidationError(
                "You can only create translations for your own lexical units."
            )

        return data


# --- Helper Serializer for Nested Input ---
class LexicalUnitInputSerializer(serializers.Serializer):
    """
    Validates the structure of individual lexical unit data provided as input
    within the bulk translation payload.
    """

    lemma = serializers.CharField(max_length=100)
    language = serializers.CharField(
        max_length=16,
        validators=[bcp47_validator, supported_language_validator],
    )
    lexical_category = serializers.ChoiceField(
        choices=LexicalCategory.choices,
    )
    part_of_speech = serializers.ChoiceField(
        choices=PartOfSpeech.choices,
    )
    pronunciation = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )


# --- Bulk Translation Serializer ---
class LexicalUnitTranslationBulkSerializer(serializers.Serializer):
    source_unit = LexicalUnitInputSerializer()
    targets = LexicalUnitInputSerializer(
        many=True, min_length=1
    )  # Ensure at least one target
    translation_type = serializers.ChoiceField(
        choices=TranslationType.choices,  # Use the enum directly for choices
        default=TranslationType.MANUAL,
    )
    confidence = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)

    def _primary_lang(self, code: str) -> str:
        """Return the primary sub-tag of a BCP-47 code (e.g., 'en' from 'en-GB')."""
        if not code:  # Handle empty or None code
            return ""
        return code.split("-")[0].lower()

    def validate(self, data):
        """
        Custom validation for the bulk operation:
        1. Source and target primary languages must differ for each translation.
        2. A unit cannot translate to itself (same canonical lemma, language, and POS).
        """
        source_data = data["source_unit"]
        source_lemma_canonical = get_canonical_lemma(source_data["lemma"])
        source_lang_primary = self._primary_lang(source_data["language"])
        source_pos = source_data["part_of_speech"]

        for target_data in data["targets"]:
            target_lemma_canonical = get_canonical_lemma(target_data["lemma"])
            target_lang_primary = self._primary_lang(target_data["language"])
            target_pos = target_data["part_of_speech"]

            # ❷ Check for different primary languages
            if source_lang_primary == target_lang_primary:
                raise serializers.ValidationError(
                    f"Source language '{source_data['language']}' and target language '{target_data['language']}' "
                    f"for lemma '{target_data['lemma']}' must have different primary language tags."
                )

            # ❶ Check for self-translation (same canonical lemma, language, and POS)
            if (
                source_lemma_canonical == target_lemma_canonical
                and source_data["language"] == target_data["language"]
                and source_pos == target_pos
            ):
                raise serializers.ValidationError(
                    f"Lexical unit '{source_lemma_canonical}' ({source_data['language']}, POS: '{source_pos}') "
                    "cannot be translated to itself."
                )
        return data

    def create(self, validated_data):
        # Get the user from the context that was passed in by the view
        request = self.context.get("request")
        if not request or not hasattr(request, "user"):
            raise serializers.ValidationError("Request context with user is required.")
        user = request.user
        source_input_data = validated_data["source_unit"]
        targets_input_data = validated_data["targets"]
        translation_type = validated_data.get(
            "translation_type", TranslationType.MANUAL
        )
        confidence = validated_data.get("confidence")

        # Set default confidence for AI translations if not provided
        if confidence is None and translation_type == TranslationType.AI:
            confidence = 0.8  # Default confidence for AI

        # 1. Get or Create the Source LexicalUnit
        source_lemma_canonical = get_canonical_lemma(source_input_data["lemma"])
        source_pos = source_input_data["part_of_speech"]

        source_unit, created_source = LexicalUnit.objects.get_or_create(
            user=user,
            lemma=source_lemma_canonical,
            language=source_input_data["language"],
            part_of_speech=source_pos,
            defaults={
                "pronunciation": source_input_data.get("pronunciation", "")
                # LexicalUnit.save() will set unit_type and handle status default
            },
        )
        # If source_unit already existed, and pronunciation was provided, update it
        if (
            not created_source
            and source_input_data.get("pronunciation")
            and source_unit.pronunciation != source_input_data.get("pronunciation")
        ):
            source_unit.pronunciation = source_input_data.get("pronunciation", "")
            source_unit.save()  # Re-save to update pronunciation

        created_translations = []

        # 2. Process each Target LexicalUnit and create translations
        for target_input_data in targets_input_data:
            target_lemma_canonical = get_canonical_lemma(target_input_data["lemma"])
            target_pos = target_input_data["part_of_speech"]

            actual_target_unit, created_target = LexicalUnit.objects.get_or_create(
                user=user,
                lemma=target_lemma_canonical,
                language=target_input_data["language"],
                part_of_speech=target_pos,
                defaults={"pronunciation": target_input_data.get("pronunciation", "")},
            )
            if (
                not created_target
                and target_input_data.get("pronunciation")
                and actual_target_unit.pronunciation
                != target_input_data.get("pronunciation")
            ):
                actual_target_unit.pronunciation = target_input_data.get(
                    "pronunciation", ""
                )
                actual_target_unit.save()

            # 3. Create (or get) the LexicalUnitTranslation link
            # Using get_or_create for the link itself to prevent duplicate translation entries
            # if the same bulk request is somehow submitted twice with identical content.
            translation_link, link_created = (
                LexicalUnitTranslation.objects.get_or_create(
                    source_unit=source_unit,
                    target_unit=actual_target_unit,
                    defaults={
                        "translation_type": translation_type,
                        "confidence": confidence,
                    },
                )
            )
            # If the link already existed, you might want to update its type/confidence:
            if not link_created:
                update_link = False
                if translation_link.translation_type != translation_type:
                    translation_link.translation_type = translation_type
                    update_link = True
                if (
                    confidence is not None and translation_link.confidence != confidence
                ):  # Check for None
                    translation_link.confidence = confidence
                    update_link = True
                if update_link:
                    translation_link.save()

            created_translations.append(translation_link)

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
        validators=[bcp47_validator, supported_language_validator],
    )
    cefr = serializers.ChoiceField(choices=CEFR.choices)


class EnrichDetailsRequestSerializer(serializers.Serializer):
    """Validates the request for the detail enrichment endpoint."""

    force_update = serializers.BooleanField(
        default=False,
        required=False,
        help_text="If true, re-fetch details even if they already exist.",
    )


class TranslateRequestSerializer(serializers.Serializer):
    """Validates the request for the translation endpoint."""

    target_language_code = serializers.CharField(
        max_length=16, validators=[bcp47_validator, supported_language_validator]
    )
