from django.urls import path, include
from rest_framework.routers import DefaultRouter

from learning.views import (
    LexicalUnitViewSet,
    LexicalUnitTranslationViewSet,
    PhraseViewSet,
    PhraseTranslationViewSet,
)

# , WordTranslationViewSet

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


urlpatterns = [
    path("", include(router.urls)),
    # path("generate-phrases/", GeneratePhrasesView.as_view(), name="generate-phrases"),
    # path("task-status/<uuid:task_id>/", TaskStatusView.as_view(), name="task-status"),
]
