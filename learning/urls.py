# learning/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from learning.views import (
    LexicalUnitViewSet,
    LexicalUnitTranslationViewSet,
    PhraseViewSet,
    PhraseTranslationViewSet,
    TaskStatusView,
    AnalyzeTextView, ExternalImportView,
)

router = DefaultRouter()
router.register(r"lexical-units", LexicalUnitViewSet, basename="lexicalunit")
router.register(
    r"lexical-unit-translations",
    LexicalUnitTranslationViewSet,
    basename="lexicalunittranslation",
)
router.register(r"phrases", PhraseViewSet, basename="phrase")
router.register(
    r"phrase-translations", PhraseTranslationViewSet, basename="phrasetranslation"
)

# New URL for the GPT import functionality
urlpatterns = [
    path("", include(router.urls)),
    path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task-status"),
    path("dictionary/analyze-text/", AnalyzeTextView.as_view(), name="analyze-text"),
    # The user_id will be used to associate the import with the correct user.
    path("import/external/user/<int:user_id>/", ExternalImportView.as_view(), name="external-import"),
]
