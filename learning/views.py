# learning/views.py
import logging

from celery.result import AsyncResult
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.filters import (
    PhraseFilter,
    LexicalUnitTranslationFilter,
    LexicalUnitFilter,
)
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
    ResolveLemmaRequestSerializer,
    AnalyzeTextRequestSerializer,
)
from learning.tasks import (
    generate_phrases_async,
    enrich_details_async,
    translate_unit_async,
    resolve_lemma_async,
    enrich_phrase_async,
    analyze_text_and_suggest_words_async,
)

logger = logging.getLogger(__name__)


class TaskQueuingMixin:
    """A mixin to handle repetitive Celery task queuing logic."""

    def _queue_task(
        self, task_func, success_message="Task queued successfully.", **kwargs
    ):
        try:
            task_result = task_func.delay(**kwargs)
            return Response(
                {"message": success_message, "task_id": task_result.id},
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as e:
            logger.error(
                f"Failed to queue task {task_func.__name__}: {e}", exc_info=True
            )
            return Response(
                {"error": "Failed to queue task."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LexicalUnitViewSet(TaskQueuingMixin, viewsets.ModelViewSet):
    serializer_class = LexicalUnitSerializer
    filterset_class = LexicalUnitFilter
    permission_classes = [IsAuthenticated]
    ordering_fields = [
        "lemma",
        "language",
        "date_added",
    ]  # Добавьте поля, по которым можно сортировать
    ordering = ["lemma"]  # Установите порядок сортировки по умолчанию

    def get_queryset(self):
        return LexicalUnit.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Create one or more Lexical Units",
        request=LexicalUnitSerializer(many=True),
    )
    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @extend_schema(
        summary="Asynchronously Resolve a Lexical Unit",
        description="Triggers a background task to find all structural variants (e.g., noun, verb) for a given lemma.",
        request=ResolveLemmaRequestSerializer,
        responses={
            202: inline_serializer(
                name="ResolveTaskQueuedResponse",
                fields={
                    "message": serializers.CharField(),
                    "task_id": serializers.UUIDField(),
                },
            )
        },
    )
    @action(detail=False, methods=["post"], url_path="resolve")
    def resolve(self, request, *args, **kwargs):
        serializer = ResolveLemmaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        return self._queue_task(
            resolve_lemma_async,
            success_message="Lemma resolution task queued.",
            lemma=data["lemma"],
            language=data["language"],
            user_id=request.user.id,
        )

    @extend_schema(
        summary="Enrich LU Details (POS, Pronunciation)",
        request=EnrichDetailsRequestSerializer,
        responses={202: {"description": "Detail enrichment task successfully queued."}},
    )
    @action(detail=True, methods=["post"], url_path="enrich-details")
    def enrich_details(self, request, pk=None):
        unit = self.get_object()
        serializer = EnrichDetailsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return self._queue_task(
            enrich_details_async,
            success_message="Detail enrichment task queued.",
            unit_id=unit.id,
            user_id=request.user.id,
            force_update=serializer.validated_data.get("force_update", False),
        )

    @extend_schema(
        summary="Translate a Lexical Unit",
        request=TranslateRequestSerializer,
        responses={202: {"description": "Translation task successfully queued."}},
    )
    @action(detail=True, methods=["post"], url_path="translate")
    def translate(self, request, pk=None):
        unit = self.get_object()
        serializer = TranslateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_lang = serializer.validated_data["target_language_code"]

        if not unit.part_of_speech:
            return Response(
                {"error": "Cannot translate. Please run 'enrich-details' first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if target_lang.lower() == unit.language.lower():
            return Response(
                {"error": "Target language cannot be the same as the source language."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._queue_task(
            translate_unit_async,
            success_message="Translation task queued.",
            unit_id=unit.id,
            user_id=request.user.id,
            target_language_code=target_lang,
        )

    @extend_schema(
        summary="Queue Phrase Generation",
        request=PhraseGenerationRequestSerializer,
        responses={202: {"description": "Phrase generation task queued successfully."}},
    )
    @action(detail=True, methods=["post"], url_path="generate-phrases")
    def generate_phrases_for_unit(self, request, pk=None):
        unit = self.get_object()
        serializer = PhraseGenerationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # The key from the validated data
        target_language = validated_data["target_language"]
        cefr_level = validated_data["cefr"]

        # The validation now uses the correct, standardised key.
        if target_language.lower() == unit.language.lower():
            return Response(
                {"error": "Target language cannot be the same as the source language."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # The call to the task queuing mixin
        return self._queue_task(
            generate_phrases_async,
            unit_id=unit.id,
            target_language=target_language,
            cefr_level=cefr_level,
        )


class LexicalUnitTranslationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = LexicalUnitTranslation.objects.select_related(
        "source_unit", "target_unit"
    ).all()
    serializer_class = LexicalUnitTranslationSerializer
    filterset_class = LexicalUnitTranslationFilter
    search_fields = ["source_unit__lemma", "target_unit__lemma"]
    ordering_fields = ["confidence"]
    ordering = ["-confidence"]

    def get_serializer_class(self):
        return (
            LexicalUnitTranslationBulkSerializer
            if self.action == "bulk_create"
            else super().get_serializer_class()
        )

    @extend_schema(
        summary="Bulk Create Translations for a Source Unit",
        request=LexicalUnitTranslationBulkSerializer,
        responses={201: LexicalUnitTranslationSerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        created_instances = serializer.save()
        response_serializer = LexicalUnitTranslationSerializer(
            created_instances, many=True
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class PhraseViewSet(TaskQueuingMixin, viewsets.ModelViewSet):
    queryset = Phrase.objects.all()
    serializer_class = PhraseSerializer
    filterset_class = PhraseFilter
    search_fields = ["text"]
    ordering_fields = ["language", "category", "cefr"]
    ordering = ["language", "category", "cefr"]

    @extend_schema(
        summary="Enrich Phrase Details",
        responses={202: {"description": "Enrichment task successfully queued."}},
    )
    @action(detail=True, methods=["post"])
    def enrich(self, request, pk=None):
        phrase = self.get_object()
        return self._queue_task(
            enrich_phrase_async,
            success_message="Phrase enrichment task queued.",
            phrase_id=phrase.id,
        )


class PhraseTranslationViewSet(viewsets.ModelViewSet):
    queryset = PhraseTranslation.objects.all()
    serializer_class = PhraseTranslationSerializer
    filterset_fields = {
        "source_phrase__language": ["exact"],
        "target_phrase__language": ["exact"],
        "source_phrase__text": ["icontains"],
        "target_phrase__text": ["icontains"],
    }
    search_fields = ["source_phrase__text", "target_phrase__text"]


class TaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Task Status and Result",
        responses={
            200: inline_serializer(
                name="TaskStatusResponse",
                fields={
                    "task_id": serializers.CharField(),
                    "status": serializers.CharField(),
                    "result": serializers.JSONField(),
                },
            )
        },
    )
    def get(self, request, task_id, *args, **kwargs):
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


class AnalyzeTextView(TaskQueuingMixin, APIView):
    """
    API endpoint to submit a text block for vocabulary analysis.
    Identifies new, unknown words for the user based on their CEFR level.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Analyze Text for New Vocabulary",
        request=AnalyzeTextRequestSerializer,
        responses={
            202: inline_serializer(
                name="AnalyzeTextTaskQueuedResponse",
                fields={
                    "message": serializers.CharField(),
                    "task_id": serializers.UUIDField(),
                },
            ),
            400: {"description": "Invalid input."},
            500: {"description": "Failed to queue task."},
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = AnalyzeTextRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text_content = serializer.validated_data["text"]

        return self._queue_task(
            analyze_text_and_suggest_words_async,
            success_message="Text analysis task queued. Check task status for results.",
            text=text_content,
            user_id=request.user.id,
        )
