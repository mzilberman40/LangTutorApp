import logging

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.decorators import action

from rest_framework.response import Response
from rest_framework import status, viewsets, serializers

from learning.models import (
    LexicalUnit,
    LexicalUnitTranslation,
    TranslationType,
    Phrase,
    PhraseTranslation,
)
from learning.serializers import (
    LexicalUnitSerializer,
    LexicalUnitTranslationSerializer,
    LexicalUnitTranslationBulkSerializer,
    PhraseSerializer,
    PhraseTranslationSerializer,
    PhraseGenerationRequestSerializer,
    EnrichLexicalUnitRequestSerializer,
)

from learning.filters import (
    PhraseFilter,
    LexicalUnitTranslationFilter,
    LexicalUnitFilter,
)
from learning.tasks import generate_phrases_async, enrich_lexical_unit_async

logger = logging.getLogger(__name__)


class LexicalUnitViewSet(viewsets.ModelViewSet):
    queryset = LexicalUnit.objects.all()
    serializer_class = LexicalUnitSerializer
    filterset_class = LexicalUnitFilter
    search_fields = ["lemma", "notes"]
    ordering_fields = ["language", "lemma"]
    ordering = ["language"]

    def create(self, request, *args, **kwargs):
        data = request.data
        is_many = isinstance(data, list)
        serializer = self.get_serializer(data=data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @extend_schema(
        summary="Queue Phrase Generation",  # Optional: A nice summary for Swagger
        description=(  # Optional: More detailed description
            "Triggers asynchronous generation of example phrases for the specified LexicalUnit. "
            "Example phrases will be generated in the LexicalUnit's own language. "
            "The request body must specify the 'target_translation_language' (into which the "
            "examples will be translated) and the 'cefr_level' for the generated examples."
        ),
        request=PhraseGenerationRequestSerializer,  # <--- THIS IS THE CRUCIAL PART
        responses={
            202: {
                "description": "Phrase generation task queued successfully. Includes task_id."
            },
            400: {
                "description": "Invalid input parameters (e.g., malformed language code, same source/target languages)."
            },
            404: {"description": "LexicalUnit not found."},
            500: {
                "description": "Failed to queue phrase generation task due to server error."
            },
        },
    )
    @action(detail=True, methods=["post"], url_path="generate-phrases")
    def generate_phrases_for_unit(self, request, pk=None):  # Renamed method for clarity
        """
        Triggers asynchronous generation of example phrases for this LexicalUnit.
        Example phrases will be generated in the LexicalUnit's own language.
        Expects 'target_translation_language' (to translate examples into)
        and 'cefr_level' (for example generation) in the request body.
        """
        unit = (
            self.get_object()
        )  # Gets the LexicalUnit instance based on pk (e.g., /api/lexical-units/1/generate-phrases/)

        request_serializer = PhraseGenerationRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                request_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = request_serializer.validated_data
        target_translation_language = validated_data["target_translation_language"]
        cefr_level = validated_data["cefr_level"]

        # The language of the LexicalUnit itself will be the language of the examples (lang2 for unit2phrases)
        example_language_code = unit.language

        # Crucial Validation: Ensure target translation language is different from the unit's own language
        if target_translation_language.lower() == example_language_code.lower():
            return Response(
                {
                    "error": "Target translation language cannot be the same as the lexical unit's language."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task_result = generate_phrases_async.delay(
                unit_id=unit.id,
                target_translation_lang_code=target_translation_language,
                cefr_level_for_phrases=cefr_level,
            )
            return Response(
                {
                    "message": "Phrase generation task queued successfully.",
                    "task_id": task_result.id,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            logger.error(
                f"Failed to queue phrase generation task for unit {unit.id}: {e}"
            )
            # Be cautious about exposing raw exception details in production
            return Response(
                {
                    "error": "Failed to queue phrase generation task. Please check server logs."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Enrich Lexical Unit",
        description=(
            "Triggers asynchronous enrichment of a LexicalUnit. "
            "This can include filling empty details (part of speech, pronunciation) "
            "and translating the unit into specified target languages."
        ),
        request=EnrichLexicalUnitRequestSerializer, # Use the new serializer
        responses={
            202: {"description": "Enrichment task queued successfully. Includes task_id."},
            400: {"description": "Invalid input parameters."},
            404: {"description": "LexicalUnit not found."}
        }
    )
    @action(detail=True, methods=['post'], url_path='enrich')
    def enrich_unit(self, request, pk=None):
        unit = self.get_object()

        serializer = EnrichLexicalUnitRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        target_languages = validated_data.get('target_translation_languages', []) # Default to empty list
        force_update = validated_data.get('force_update_details', False)

        try:
            task_result = enrich_lexical_unit_async.delay(
                unit_id=unit.id,
                target_language_codes=target_languages,
                force_update=force_update
            )
            return Response(
                {"message": "Lexical unit enrichment task queued.", "task_id": task_result.id},
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            logger.error(f"Failed to queue enrichment task for unit {unit.id}: {e}")
            return Response(
                {"error": "Failed to queue enrichment task."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LexicalUnitTranslationViewSet(viewsets.ModelViewSet):
    queryset = LexicalUnitTranslation.objects.all()
    serializer_class = LexicalUnitTranslationSerializer
    filterset_class = LexicalUnitTranslationFilter
    search_fields = [
        "source_unit__lemma",
        "target_unit__lemma",
    ]
    ordering_fields = ["confidence"]
    ordering = ["-confidence"]

    def get_serializer_class(self):
        if self.action == "bulk_create":
            return LexicalUnitTranslationBulkSerializer
        return super().get_serializer_class()

    @extend_schema(
        operation_id="lexicalunittranslation_bulk_create",
        description=(
            "Create several translations for one **source_unit** in a single request. "
            "Fields such as pronunciation, part_of_speech and confidence must be "
            "supplied by SilverTranslator."
        ),
        request=inline_serializer(
            name="BulkLexicalUnitTranslationCreate",  # ⬅ renamed
            fields={
                "source_unit": serializers.DictField(),  # ⬅ renamed
                "targets": serializers.ListField(
                    child=serializers.DictField(), min_length=1
                ),
                "translation_type": serializers.ChoiceField(
                    choices=[c[0] for c in TranslationType.choices], required=False
                ),
                "confidence": serializers.FloatField(required=False),
            },
        ),
        responses={201: LexicalUnitTranslationSerializer(many=True)},
    )
    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        serializer = LexicalUnitTranslationBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = serializer.save()
        return Response(
            LexicalUnitTranslationSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class PhraseViewSet(viewsets.ModelViewSet):
    queryset = Phrase.objects.all()
    serializer_class = PhraseSerializer
    filterset_class = PhraseFilter
    search_fields = ["text"]
    ordering_fields = ["language", "category", "cefr"]
    ordering = ["language", "category", "cefr"]


class PhraseTranslationViewSet(viewsets.ModelViewSet):
    queryset = PhraseTranslation.objects.all()
    serializer_class = PhraseTranslationSerializer
    filterset_fields = {
        "source_phrase__language": ["exact"],
        "target_phrase__language": ["exact"],
        "source_phrase__text": ["icontains"],
        "target_phrase__text": ["icontains"],
    }
    search_fields = [
        "source_phrase__text",
        "target_phrase__text",
    ]
    # ordering_fields = ["cefr"]
    # ordering = ["cefr"]
