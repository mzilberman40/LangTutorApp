# In learning/tests/test_models.py

import pytest
from django.db import IntegrityError
from learning.models import LexicalUnit, LexicalUnitTranslation
from learning.enums import (
    LexicalUnitType,
    LexicalUnitStatus,
    PartOfSpeech,
)  # Assuming UnitStatus from your enums.py

pytestmark = pytest.mark.django_db

# --- LexicalUnit Model Tests ---


class TestLexicalUnitModel:

    def test_lu_uniqueness_exact_duplicate_fails(self):
        """Tests creating an exact duplicate fails."""
        LexicalUnit.objects.create(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        with pytest.raises(IntegrityError):
            LexicalUnit.objects.create(
                lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
            )

    def test_lu_uniqueness_different_case_lemma_fails(self):
        """Tests duplicate lemma with different case fails due to .lower() in save()."""
        LexicalUnit.objects.create(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        with pytest.raises(IntegrityError):
            LexicalUnit.objects.create(
                lemma="Test", language="en", part_of_speech=PartOfSpeech.NOUN
            )

    def test_lu_uniqueness_allows_different_pos(self):
        """Tests that different part_of_speech allows creation."""
        LexicalUnit.objects.create(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        lu_verb = LexicalUnit.objects.create(
            lemma="test", language="en", part_of_speech=PartOfSpeech.VERB
        )  # Should succeed
        assert lu_verb.part_of_speech == PartOfSpeech.VERB

    def test_lu_uniqueness_allows_different_language(self):
        """Tests that different language allows creation."""
        LexicalUnit.objects.create(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        lu_fr = LexicalUnit.objects.create(
            lemma="test", language="fr", part_of_speech=PartOfSpeech.NOUN
        )  # Should succeed
        assert lu_fr.language == "fr"

    def test_lu_uniqueness_allows_different_lemma(self):
        """Tests that different lemma allows creation."""
        LexicalUnit.objects.create(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        lu_other = LexicalUnit.objects.create(
            lemma="another", language="en", part_of_speech=PartOfSpeech.NOUN
        )  # Should succeed
        assert lu_other.lemma == "another"

    def test_lu_can_be_created_with_empty_pos_string(self):
        """Tests that a LexicalUnit can be created with an empty string for part_of_speech."""
        lu = LexicalUnit.objects.create(
            lemma="test_empty_pos_creation", language="en", part_of_speech=""
        )
        assert lu.pk is not None  # Check it was created
        assert lu.part_of_speech == ""

    def test_lu_duplicate_with_empty_pos_string_raises_integrity_error(self):
        """Tests that creating a duplicate LU (including empty POS) raises IntegrityError."""
        LexicalUnit.objects.create(
            lemma="test_empty_pos_duplicate", language="en", part_of_speech=""
        )
        with pytest.raises(IntegrityError):
            LexicalUnit.objects.create(
                lemma="test_empty_pos_duplicate", language="en", part_of_speech=""
            )

    def test_lu_same_lemma_lang_but_different_actual_pos_succeeds(self):
        """
        Tests creating an LU with an actual POS succeeds even if one with an empty POS exists
        for the same lemma and language.
        """
        # First, create the one with an empty POS
        LexicalUnit.objects.create(
            lemma="test_empty_pos_vs_actual_pos", language="en", part_of_speech=""
        )

        # Now, create one with the same lemma/language but an actual POS
        lu_noun_version = LexicalUnit.objects.create(
            lemma="test_empty_pos_vs_actual_pos",
            language="en",
            part_of_speech=PartOfSpeech.NOUN,
        )
        assert lu_noun_version.pk is not None  # Check it was created
        assert lu_noun_version.part_of_speech == PartOfSpeech.NOUN

    def test_lexical_unit_defaults_and_initial_save_behavior(self):
        """
        Tests default values and basic impact of save() method on a new instance.
        """
        # Note: 'status' was LexicalUnitStatus.LEARNING in your enums.py, but your model used UnitStatus
        # I'll use LexicalUnitStatus here, please adjust if your enum is named UnitStatus
        lu = LexicalUnit.objects.create(
            lemma="  MeLoN  ", language="en-GB", part_of_speech=PartOfSpeech.NOUN
        )
        assert lu.status == LexicalUnitStatus.LEARNING  # Check default status
        assert lu.notes == ""  # Check default notes
        assert lu.lemma == "melon"  # Check .lower() and stripping from save()
        assert lu.unit_type == LexicalUnitType.SINGLE  # Check unit_type from save()

    def test_lexical_unit_str_representation(self):
        """Tests the __str__ method."""
        lu_no_pos = LexicalUnit.objects.create(
            lemma="str_test", language="en", part_of_speech=""
        )
        assert str(lu_no_pos) == "str_test [en]"

        lu_with_pos = LexicalUnit.objects.create(
            lemma="str_test_pos", language="fr", part_of_speech=PartOfSpeech.ADJ
        )
        assert str(lu_with_pos) == "str_test_pos (adj) [fr]"

    # --- Comprehensive tests for save() method's canonicalization and unit_type setting ---
    # These tests consolidate and expand upon your previous canonicalization tests
    # and my earlier suggestions.

    def test_save_strips_spaces_lower_type_single(self):
        lu = LexicalUnit.objects.create(
            lemma="  WoRd  ", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        assert lu.lemma == "word"
        assert lu.unit_type == LexicalUnitType.SINGLE

    def test_save_strips_spaces_lower_type_colloc(self):
        lu = LexicalUnit.objects.create(
            lemma="  TeSt   CoLlOcAtIoN  ",
            language="en",
            part_of_speech=PartOfSpeech.COLLOCATION,
        )
        assert lu.lemma == "test collocation"
        assert lu.unit_type == LexicalUnitType.COLLOC

    def test_save_internal_spaces_lower_type_colloc(self):
        lu = LexicalUnit.objects.create(
            lemma="WORD   WITH  SPACES",
            language="en",
            part_of_speech=PartOfSpeech.COLLOCATION,
        )
        assert lu.lemma == "word with spaces"
        assert lu.unit_type == LexicalUnitType.COLLOC

    def test_save_already_canonical_single_word(self):
        lu = LexicalUnit.objects.create(
            lemma="canonical", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        assert lu.lemma == "canonical"
        assert lu.unit_type == LexicalUnitType.SINGLE

    def test_save_already_canonical_collocation(self):
        lu = LexicalUnit.objects.create(
            lemma="already canonical form",
            language="en",
            part_of_speech=PartOfSpeech.COLLOCATION,
        )
        assert lu.lemma == "already canonical form"
        assert lu.unit_type == LexicalUnitType.COLLOC

    def test_save_empty_lemma_sets_type_single(self):
        lu = LexicalUnit.objects.create(lemma="", language="en", part_of_speech="")
        assert lu.lemma == ""
        assert lu.unit_type == LexicalUnitType.SINGLE

    def test_save_all_spaces_lemma_becomes_empty_sets_type_single(self):
        lu = LexicalUnit.objects.create(lemma="   ", language="en", part_of_speech="")
        assert lu.lemma == ""
        assert lu.unit_type == LexicalUnitType.SINGLE

    def test_save_preserves_internal_hyphens_sets_type_single(self):
        # "state-of-the-art" has no spaces after canonicalization, so type is SINGLE
        lu = LexicalUnit.objects.create(
            lemma="  STATE-OF-THE-ART  ", language="en", part_of_speech=PartOfSpeech.ADJ
        )
        assert lu.lemma == "state-of-the-art"
        assert lu.unit_type == LexicalUnitType.SINGLE

    def test_save_preserves_internal_apostrophes_sets_type_colloc(self):
        # Use a valid POS from your enum, e.g., COLLOCATION if you added it, or "" if appropriate
        lu = LexicalUnit.objects.create(
            lemma="  IT'S  A  TEST  ",
            language="en",
            part_of_speech=PartOfSpeech.COLLOCATION,
        )
        assert lu.lemma == "it's a test"
        assert lu.unit_type == LexicalUnitType.COLLOC

    def test_save_lemma_with_just_one_word_is_single(self):
        lu = LexicalUnit.objects.create(
            lemma="TAKE", language="en-gb", part_of_speech=PartOfSpeech.VERB
        )
        assert lu.lemma == "take"
        assert lu.unit_type == LexicalUnitType.SINGLE

    def test_save_collocation_is_colloc(self):
        # This was your test_lexical_unit_two_words(), now more specific
        lu = LexicalUnit.objects.create(
            lemma="  TAKE OFF  ",
            language="en-GB",
            part_of_speech=PartOfSpeech.PHRASAL_VERB,
        )  # Example POS
        assert lu.lemma == "take off"
        assert lu.status == LexicalUnitStatus.LEARNING  # Default status
        assert lu.notes == ""  # Default notes
        assert lu.unit_type == LexicalUnitType.COLLOC


# --- LexicalUnitTranslation Model Tests ---


class TestLexicalUnitTranslationModel:

    @pytest.fixture
    def sample_units(self):
        # Fixture to provide sample LUs for translation tests
        # Ensures POS is provided due to unique_together constraint
        unit1 = LexicalUnit.objects.create(
            lemma="apple", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        unit2 = LexicalUnit.objects.create(
            lemma="яблоко", language="ru", part_of_speech=PartOfSpeech.NOUN
        )
        unit3 = LexicalUnit.objects.create(
            lemma="pen", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        unit4 = LexicalUnit.objects.create(
            lemma="ручка", language="ru", part_of_speech=PartOfSpeech.NOUN
        )
        return unit1, unit2, unit3, unit4

    def test_lexical_unit_translation_uniqueness(self, sample_units):
        w1, w2, _, _ = sample_units
        LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)
        with pytest.raises(IntegrityError):
            LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)

    def test_lexical_unit_translation_str_representation(self, sample_units):
        # Renamed from test_lexical_unit_translation_str for clarity
        w1, w2, _, _ = sample_units
        w1.lemma = "cat"  # Override for specific test string
        w1.save()
        w2.lemma = "кот"  # Override for specific test string
        w2.save()

        trans = LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)
        # Assuming the updated __str__ method in LexicalUnit: "lemma (pos) [lang]" or "lemma [lang]"
        # And __str__ in LexicalUnitTranslation: f"{self.source_unit} → {self.target_unit}"
        # You'll need to ensure your LexicalUnit __str__ method is as discussed.
        # For this test, I'll assume a simple "lemma [lang]" if POS is empty for the fixture LUs.
        # Or, if they always get a POS from create, then "lemma (pos) [lang]"
        # Let's make fixture LUs have explicit POS for predictable __str__
        w1_str = str(w1)  # e.g., "cat (noun) [en]"
        w2_str = str(w2)  # e.g., "кот (noun) [ru]"
        assert str(trans) == f"{w1_str} → {w2_str}"

    def test_lexical_unit_translation_fields_and_defaults(self, sample_units):
        # Renamed from test_word_translation_str_and_fields
        w1, w2, _, _ = sample_units
        w1.lemma = "river"
        w1.save()  # For consistent test case
        w2.lemma = "река"
        w2.save()

        t = LexicalUnitTranslation.objects.create(
            source_unit=w1, target_unit=w2, translation_type="ai", confidence=0.88
        )
        # Re-evaluate __str__ based on potential POS in LexicalUnit's __str__
        w1_str = str(w1)
        w2_str = str(w2)
        assert str(t) == f"{w1_str} → {w2_str}"
        assert t.translation_type == "ai"  # Check passed value
        assert t.confidence == 0.88  # Check passed value

        # Check default translation_type
        t_default = LexicalUnitTranslation.objects.create(
            source_unit=w2, target_unit=w1
        )
        assert (
            t_default.translation_type == "manual"
        )  # Assuming 'manual' is the default in your model

    def test_lexical_unit_translation_reverse_direction_allowed(self, sample_units):
        # Renamed from test_word_translation_reverse_direction_allowed
        _, _, w3, w4 = sample_units  # Using pen, ручка
        t1 = LexicalUnitTranslation.objects.create(source_unit=w3, target_unit=w4)
        t2 = LexicalUnitTranslation.objects.create(
            source_unit=w4, target_unit=w3
        )  # Reverse
        assert t1.source_unit == w3
        assert t2.source_unit == w4
        assert t1 != t2
