# In learning/tests/test_models.py

import pytest
from django.db import IntegrityError
from learning.enums import (
    LexicalUnitType,
    LexicalUnitStatus,
    PartOfSpeech,
)
from learning.models import LexicalUnitTranslation, LexicalUnit

# All tests in this file will be run against the database
pytestmark = pytest.mark.django_db

# --- LexicalUnit Model Tests ---


class TestLexicalUnitModel:

    # Each test now accepts the `lexical_unit_factory` fixture as an argument.
    # This factory is defined in `learning/tests/conftest.py`.

    def test_lu_uniqueness_exact_duplicate_fails(self, lexical_unit_factory):
        """Tests creating an exact duplicate fails FOR THE SAME USER."""
        lexical_unit_factory(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        with pytest.raises(IntegrityError):
            lexical_unit_factory(
                lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
            )

    def test_lu_uniqueness_allows_same_lemma_for_different_users(
        self, user_factory, lexical_unit_factory
    ):
        """
        Tests that the uniqueness constraint is per-user. The same lemma can
        exist for different users.
        """
        # The first LU is created for the default user via the factory
        lexical_unit_factory(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )

        # Create a second, different user
        other_user = user_factory(username="otheruser")

        # Create the same LU but explicitly for the other user. This should succeed.
        lu_other_user = lexical_unit_factory(
            lemma="test",
            language="en",
            part_of_speech=PartOfSpeech.NOUN,
            user=other_user,
        )
        assert lu_other_user.user == other_user
        assert LexicalUnit.objects.count() == 2

    def test_lu_uniqueness_different_case_lemma_fails(self, lexical_unit_factory):
        """Tests duplicate lemma with different case fails due to .lower() in save()."""
        lexical_unit_factory(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        with pytest.raises(IntegrityError):
            lexical_unit_factory(
                lemma="Test", language="en", part_of_speech=PartOfSpeech.NOUN
            )

    def test_lu_uniqueness_allows_different_pos(self, lexical_unit_factory):
        """Tests that different part_of_speech allows creation."""
        lexical_unit_factory(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        lu_verb = lexical_unit_factory(
            lemma="test", language="en", part_of_speech=PartOfSpeech.VERB
        )
        assert lu_verb.part_of_speech == PartOfSpeech.VERB

    def test_lu_uniqueness_allows_different_language(self, lexical_unit_factory):
        """Tests that different language allows creation."""
        lexical_unit_factory(
            lemma="test", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        lu_fr = lexical_unit_factory(
            lemma="test", language="fr", part_of_speech=PartOfSpeech.NOUN
        )
        assert lu_fr.language == "fr"

    def test_lexical_unit_defaults_and_initial_save_behavior(
        self, lexical_unit_factory
    ):
        """Tests default values and basic impact of save() method on a new instance."""
        lu = lexical_unit_factory(
            lemma="  MeLoN  ", language="en-GB", part_of_speech=PartOfSpeech.NOUN
        )
        assert lu.status == LexicalUnitStatus.LEARNING
        assert lu.notes == ""
        assert lu.lemma == "melon"
        assert lu.unit_type == LexicalUnitType.SINGLE

    def test_lexical_unit_str_representation(self, lexical_unit_factory):
        """Tests the __str__ method."""
        lu_with_pos = lexical_unit_factory(
            lemma="str_test_pos", language="fr", part_of_speech=PartOfSpeech.ADJ
        )
        # The __str__ method should now include the user
        assert (
            str(lu_with_pos) == f"str_test_pos (adj) [fr] ({lu_with_pos.user.username})"
        )


# --- LexicalUnitTranslation Model Tests ---


class TestLexicalUnitTranslationModel:

    # The fixture providing sample units is refactored to use the factory
    @pytest.fixture
    def sample_units(self, lexical_unit_factory):
        """Fixture to provide sample LUs for translation tests."""
        unit1 = lexical_unit_factory(
            lemma="apple", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        unit2 = lexical_unit_factory(
            lemma="яблоко", language="ru", part_of_speech=PartOfSpeech.NOUN
        )
        unit3 = lexical_unit_factory(
            lemma="pen", language="en", part_of_speech=PartOfSpeech.NOUN
        )
        unit4 = lexical_unit_factory(
            lemma="ручка", language="ru", part_of_speech=PartOfSpeech.NOUN
        )
        return unit1, unit2, unit3, unit4

    def test_lexical_unit_translation_uniqueness(self, sample_units):
        w1, w2, _, _ = sample_units
        LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)
        with pytest.raises(IntegrityError):
            LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)

    def test_lexical_unit_translation_str_representation(self, sample_units):
        w1, w2, _, _ = sample_units
        trans = LexicalUnitTranslation.objects.create(source_unit=w1, target_unit=w2)
        # The __str__ representation automatically inherits the new user-aware string from the LU model
        assert str(trans) == f"{str(w1)} → {str(w2)}"
