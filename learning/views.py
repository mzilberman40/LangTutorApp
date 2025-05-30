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
)

from learning.filters import (
    PhraseFilter,
    LexicalUnitTranslationFilter,
    LexicalUnitFilter,
)

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
