# learning/serializers/__init__.py
from .base import LanguageField
from .external import ExternalImportSerializer, ExternalTextPayloadSerializer
from .lexical_units import (
    LexicalUnitSerializer,
    LexicalUnitTranslationSerializer,
    LexicalUnitTranslationBulkSerializer,
)
from .phrases import PhraseSerializer, PhraseTranslationSerializer
from .tasks import (
    ResolveLemmaRequestSerializer,
    ResolvedLemmaResponseSerializer,
    PhraseGenerationRequestSerializer,
    EnrichDetailsRequestSerializer,
    TranslateRequestSerializer,
    AnalyzeTextRequestSerializer,
)

# This makes the serializers available under the learning.serializers namespace
__all__ = [
    "LanguageField",
    "ExternalImportSerializer",
    "ExternalTextPayloadSerializer",
    "LexicalUnitSerializer",
    "LexicalUnitTranslationSerializer",
    "LexicalUnitTranslationBulkSerializer",
    "PhraseSerializer",
    "PhraseTranslationSerializer",
    "ResolveLemmaRequestSerializer",
    "ResolvedLemmaResponseSerializer",
    "PhraseGenerationRequestSerializer",
    "EnrichDetailsRequestSerializer",
    "TranslateRequestSerializer",
    "AnalyzeTextRequestSerializer",
]