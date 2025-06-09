import logging

from celery.result import AsyncResult
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets, serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework.views import APIView

from ai.client import get_client
from learning.models import (
    LexicalUnit,
    LexicalUnitTranslation,
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
    TranslateRequestSerializer,
    EnrichDetailsRequestSerializer,
    ResolvedLemmaResponseSerializer,
    ResolveLemmaRequestSerializer,
)

from learning.filters import (
    PhraseFilter,
    LexicalUnitTranslationFilter,
    LexicalUnitFilter,
)
from learning.tasks import (
    generate_phrases_async,
    enrich_details_async,
    translate_unit_async,
    resolve_lemma_async,
)
from learning.utils import get_canonical_lemma
from services.get_lemma_details import get_lemma_details

logger = logging.getLogger(__name__)


class LexicalUnitViewSet(viewsets.ModelViewSet):
    serializer_class = LexicalUnitSerializer
    filterset_class = LexicalUnitFilter
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This method ensures that any request (GET, PUT, DELETE) to this
        viewset will ONLY ever operate on the objects owned by the
        currently authenticated user.
        """
        return LexicalUnit.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        When a new Lexical Unit is created via a POST request, this method
        intercepts the save process and automatically injects the current
        user into the object before it's saved to the database.
        """
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Create one or more Lexical Units",
        description="Create a single Lexical Unit by sending a JSON object, or multiple Lexical Units by sending a list of objects.",
        examples=[
            OpenApiExample(
                "Create a single Lexical Unit",
                description="A complete example for creating a single lexical unit.",
                value={
                    "lemma": "example",
                    "language": "en-US",
                    "part_of_speech": "noun",
                    "status": "learning",
                    "notes": "A good example word.",
                    "pronunciation": "/ɪɡˈzæmpəl/",
                },
                request_only=True,  # This example is for the request body
            ),
            OpenApiExample(
                "Create multiple Lexical Units (Bulk)",
                description="An example of bulk-creating multiple lexical units in a single request.",
                value=[
                    {"lemma": "first", "language": "en-GB", "part_of_speech": "adj"},
                    {"lemma": "второй", "language": "ru", "part_of_speech": "num"},
                ],
                request_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        """
        Handles both single and bulk creation for Lexical Units.
        """
        # Check if the incoming data is a list for bulk creation
        is_many = isinstance(request.data, list)

        # Instantiate the serializer. The 'many=is_many' part is crucial.
        # It tells DRF to expect a list if is_many is True.
        serializer = self.get_serializer(data=request.data, many=is_many)

        serializer.is_valid(raise_exception=True)

        # The perform_create method handles saving and assigning the user
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @extend_schema(
        summary="Enrich LU Details (POS, Pronunciation)",
        description=(
            "Triggers an asynchronous task to fetch details (all applicable Parts of Speech and their pronunciations) "
            "for this LexicalUnit. This will resolve an underspecified LU into one or more specific variants in the database."
        ),
        request=EnrichDetailsRequestSerializer,
        responses={202: {"description": "Detail enrichment task successfully queued."}},
    )
    @action(detail=True, methods=["post"], url_path="enrich-details")
    def enrich_details(self, request, pk=None):
        unit = self.get_object()
        serializer = EnrichDetailsRequestSerializer(data=request.data)
        serializer.is_valid(
            raise_exception=True
        )  # Ensures force_update is a boolean if provided
        force_update = serializer.validated_data.get("force_update", False)

        try:
            task_result = enrich_details_async.delay(
                unit_id=unit.id,
                user_id=request.user.id,
                force_update=force_update,
            )
            return Response(
                {
                    "message": "Detail enrichment task queued.",
                    "task_id": task_result.id,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            logger.error(
                f"Failed to queue detail enrichment task for unit {unit.id}: {e}"
            )
            return Response(
                {"error": "Failed to queue task."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Translate a Lexical Unit",
        description=(
            "Triggers an asynchronous task to translate this specific LexicalUnit into a new target language. "
            "Best used on a unit that already has a specific Part of Speech."
        ),
        request=TranslateRequestSerializer,
        responses={
            202: {"description": "Translation task successfully queued."},
            400: {
                "description": "Invalid request (e.g., missing target language, source and target languages are the same, or source POS is not specified)."
            },
        },
    )
    @action(detail=True, methods=["post"], url_path="translate")
    def translate(self, request, pk=None):
        unit = self.get_object()
        serializer = TranslateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_lang = serializer.validated_data["target_language_code"]

        # It's good practice to only allow translation for units with a defined POS
        if not unit.part_of_speech:
            return Response(
                {
                    "error": "Cannot translate a Lexical Unit with an unspecified Part of Speech. Please run 'enrich-details' first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target_lang.lower() == unit.language.lower():
            return Response(
                {"error": "Target language cannot be the same as the source language."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task_result = translate_unit_async.delay(
                unit_id=unit.id,
                user_id=request.user.id,
                target_language_code=target_lang,
            )
            return Response(
                {"message": "Translation task queued.", "task_id": task_result.id},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            logger.error(f"Failed to queue translation task for unit {unit.id}: {e}")
            return Response(
                {"error": "Failed to queue task."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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


class LexicalUnitTranslationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for creating, retrieving, updating, and deleting Lexical Unit Translations.
    Includes a custom action for bulk creation of translations for a single source unit.
    """

    permission_classes = [IsAuthenticated]

    queryset = LexicalUnitTranslation.objects.select_related(
        "source_unit", "target_unit"
    ).all()
    serializer_class = LexicalUnitTranslationSerializer
    filterset_class = LexicalUnitTranslationFilter
    search_fields = [
        "source_unit__lemma",
        "target_unit__lemma",
    ]
    ordering_fields = ["confidence"]
    ordering = ["-confidence"]

    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the action.
        For 'bulk_create', it uses the bulk serializer.
        """
        if self.action == "bulk_create":
            return LexicalUnitTranslationBulkSerializer
        return super().get_serializer_class()

    @extend_schema(
        summary="Bulk Create Translations for a Source Unit",
        description=(
            "Create several translations for one source lexical unit in a single request. "
            "If the source unit or any target units do not exist, they will be created."
        ),
        request=LexicalUnitTranslationBulkSerializer,
        responses={201: LexicalUnitTranslationSerializer(many=True)},
        # 👇 ADD THIS 'examples' PARAMETER 👇
        examples=[
            OpenApiExample(
                "Example 1: Translate a collocation to two languages",
                summary='Translate "take off" to Russian and French',
                description="A complete example for creating a source collocation and two targets.",
                value={
                    "source_unit": {
                        "lemma": "take off",
                        "language": "en-GB",
                        "part_of_speech": "phrasal_verb",  # Assuming this is in your enum
                        "pronunciation": "/teɪk ɒf/",
                    },
                    "targets": [
                        {
                            "lemma": "взлетать",
                            "language": "ru",
                            "part_of_speech": "verb",
                            "pronunciation": "[vzlʲɪˈtatʲ]",
                        },
                        {
                            "lemma": "décoller",
                            "language": "fr-FR",
                            "part_of_speech": "verb",
                            "pronunciation": "/de.kɔ.le/",
                        },
                    ],
                    "translation_type": "ai",
                    "confidence": 0.95,
                },
            ),
        ],
    )
    @action(detail=False, methods=["post"], url_path="bulk-create")  # Explicit url_path
    def bulk_create(self, request, *args, **kwargs):
        """
        Custom action to create multiple LexicalUnitTranslation objects from a single
        source lexical unit to multiple target units.
        """
        # get_serializer_class() will correctly provide LexicalUnitTranslationBulkSerializer
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        created_instances = serializer.save()

        # We then serialize the created *translation link* objects for the response
        response_serializer = LexicalUnitTranslationSerializer(
            created_instances, many=True
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


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


class ResolveAndCreateLemmaView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Asynchronously Resolve a Lexical Unit",
        request=ResolveLemmaRequestSerializer,
        responses={
            202: inline_serializer(
                name="ResolveTaskQueuedResponse",
                fields={
                    "message": serializers.CharField(),
                    "task_id": serializers.UUIDField(),
                },
            ),
            400: {"description": "Invalid input."},
        },
    )
    def post(self, request, *args, **kwargs):
        request_serializer = ResolveLemmaRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        canonical_lemma = get_canonical_lemma(data["lemma"])
        language = data["language"]

        # --- The entire logic is now replaced by a single task call ---
        task = resolve_lemma_async.delay(
            lemma=canonical_lemma, language=language, user_id=request.user.id
        )

        return Response(
            {"message": "Lemma resolution task queued.", "task_id": task.id},
            status=status.HTTP_202_ACCEPTED,
        )


class TaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id, *args, **kwargs):
        """
        Retrieves the status and result of a Celery task.
        """
        task_result = AsyncResult(task_id)

        response_data = {
            "task_id": task_id,
            "status": task_result.status,
            "result": (
                task_result.result
                if task_result.successful()
                else str(task_result.result)
            ),
        }

        return Response(response_data, status=status.HTTP_200_OK)


# class ResolveAndCreateLemmaView(APIView):
#     """
#     A smart endpoint to handle Lexical Unit creation.
#     - If POS is provided, it creates the LU synchronously.
#     - If POS is omitted, it calls an LLM to find possible POS variants and returns them
#       to the client without creating anything.
#     """
#
#     permission_classes = []  # Add your permission classes, e.g., [IsAuthenticated]
#
#     @extend_schema(
#         summary="Resolve or Create a Lexical Unit",
#         request=ResolveLemmaRequestSerializer,
#         responses={
#             201: LexicalUnitSerializer,  # For the case where an LU is created directly
#             200: ResolvedLemmaResponseSerializer,  # For the case where variants are returned
#             400: {
#                 "description": "Invalid input or a resolvable lemma that already has a specific POS variant in the database."
#             },
#             404: {
#                 "description": "LLM could not resolve the lemma into any valid Parts of Speech."
#             },
#         },
#     )
#     def post(self, request, *args, **kwargs):
#         request_serializer = ResolveLemmaRequestSerializer(data=request.data)
#         request_serializer.is_valid(raise_exception=True)
#         data = request_serializer.validated_data
#
#         canonical_lemma = get_canonical_lemma(data["lemma"])
#         language = data["language"]
#
#         # This part of the logic for direct creation is fine.
#         # Note: I've added `user=request.user` to the get_or_create call.
#         pos = data.get("part_of_speech")
#         if pos:
#             lu, created = LexicalUnit.objects.get_or_create(
#                 user=request.user,  # <-- Important addition
#                 lemma=canonical_lemma,
#                 language=language,
#                 part_of_speech=pos,
#                 defaults={"pronunciation": data.get("pronunciation", "")},
#             )
#             response_serializer = LexicalUnitSerializer(lu)
#             status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
#             return Response(response_serializer.data, status=status_code)
#
#         # The logic for when Part of Speech IS NOT provided needs updating.
#         else:
#             client = get_client()
#             temp_lu = LexicalUnit(lemma=canonical_lemma, language=language)
#             llm_variants = get_lemma_details(client, temp_lu)
#
#             if not llm_variants:
#                 return Response(
#                     {"error": f"Could not resolve the lemma '{canonical_lemma}'."},
#                     status=status.HTTP_404_NOT_FOUND,
#                 )
#
#             ## --- START: NEW LOGIC TO ADD 'exists' FLAG --- ##
#
#             # 1. Get a set of PoS that already exist FOR THIS USER.
#             existing_pos_for_user = set(
#                 LexicalUnit.objects.filter(
#                     user=request.user, lemma=canonical_lemma, language=language
#                 ).values_list("part_of_speech", flat=True)
#             )
#
#             # 2. Process the LLM results, adding the 'exists' flag to each.
#             processed_variants = []
#             for variant in llm_variants:
#                 variant["exists"] = (
#                     variant.get("part_of_speech") in existing_pos_for_user
#                 )
#                 processed_variants.append(variant)
#
#             ## --- END: NEW LOGIC --- ##
#
#             response_data = {
#                 "lemma": canonical_lemma,
#                 "language": language,
#                 # Use the newly processed list instead of the raw LLM response
#                 "variants": processed_variants,
#             }
#             # Note: Your response serializer needs to be updated to handle the `exists` field.
#             # I will assume ResolvedLemmaVariantSerializer is updated to:
#             # class ResolvedLemmaVariantSerializer(serializers.Serializer):
#             #     part_of_speech = serializers.CharField()
#             #     pronunciation = serializers.CharField(allow_blank=True, allow_null=True)
#             #     exists = serializers.BooleanField()
#             return Response(response_data, status=status.HTTP_200_OK)
