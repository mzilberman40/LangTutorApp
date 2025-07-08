# learning/admin.py
from django.contrib import admin
from .models import (
    LexicalUnit,
    LexicalUnitTranslation,
    Phrase,
    PhraseTranslation,
    # Lesson,
    # LessonPhrase,
    # LessonFile,
)


@admin.register(LexicalUnit)
class LexicalUnitAdmin(admin.ModelAdmin):
    """Admin configuration for the LexicalUnit model."""

    list_display = (
        "id",  # --- CHANGE HERE ---
        "lemma",
        "language",
        "part_of_speech",
        "lexical_category",
        "user",
        "validation_status",
        "date_added",
    )
    list_filter = (
        "language",
        "status",
        "validation_status",
        "lexical_category",
        "user",
    )
    search_fields = ("lemma",)
    readonly_fields = ("date_added", "last_reviewed")
    list_per_page = 25


@admin.register(Phrase)
class PhraseAdmin(admin.ModelAdmin):
    """Admin configuration for the Phrase model."""

    list_display = (
        "id",  # --- CHANGE HERE ---
        "text",
        "language",
        "cefr",
        "category",
        "validation_status",
    )
    list_filter = ("language", "cefr", "category", "validation_status")
    search_fields = ("text",)
    filter_horizontal = ("units",)
    list_per_page = 25


@admin.register(LexicalUnitTranslation)
class LexicalUnitTranslationAdmin(admin.ModelAdmin):
    """Admin configuration for LexicalUnitTranslation."""

    list_display = (
        "id",  # --- CHANGE HERE ---
        "source_unit",
        "target_unit",
        "translation_type",
        "validation_status",
    )
    list_filter = ("translation_type", "validation_status")
    search_fields = ("source_unit__lemma", "target_unit__lemma")
    autocomplete_fields = ["source_unit", "target_unit"]


@admin.register(PhraseTranslation)
class PhraseTranslationAdmin(admin.ModelAdmin):
    """Admin configuration for PhraseTranslation."""

    list_display = ("id", "source_phrase", "target_phrase")  # --- CHANGE HERE ---
    search_fields = ("source_phrase__text", "target_phrase__text")
    autocomplete_fields = ["source_phrase", "target_phrase"]


# # --- Lesson Admin Configuration ---
#
# class LessonPhraseInline(admin.TabularInline):
#     """Allows editing LessonPhrase objects directly within the Lesson admin page."""
#     model = LessonPhrase
#     extra = 1
#     autocomplete_fields = ['phrase']
#
# class LessonFileInline(admin.TabularInline):
#     """Allows editing LessonFile objects directly within the Lesson admin page."""
#     model = LessonFile
#     extra = 1
#
# @admin.register(Lesson)
# class LessonAdmin(admin.ModelAdmin):
#     """Admin configuration for the Lesson model."""
#     list_display = (
#         'id', # --- CHANGE HERE ---
#         '__str__',
#         'user',
#         'created_at'
#     )
#     list_filter = ('user',)
#     inlines = [LessonPhraseInline, LessonFileInline]
#     filter_horizontal = ('phrases',)
