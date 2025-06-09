import pytest
from django.urls import reverse
from learning.models import LexicalUnit
from learning.enums import PartOfSpeech

# All tests in this file will be run against the database
pytestmark = pytest.mark.django_db


# The `authenticated_client` fixture logs in the `default_user` for all tests in this class.
class TestLexicalUnitAPI:

    def test_create_lexical_unit_single_word(self, authenticated_client, default_user):
        url = reverse("lexicalunit-list")
        payload = {
            "lemma": "  TesTWord  ",
            "language": "en-GB",
            "part_of_speech": PartOfSpeech.NOUN,
        }
        response = authenticated_client.post(url, payload, format="json")
        assert response.status_code == 201

        lu = LexicalUnit.objects.get(id=response.data["id"])
        assert lu.user == default_user  # Verify ownership
        assert lu.lemma == "testword"

    def test_create_duplicate_lexical_unit_for_same_user_fails(
        self, authenticated_client
    ):
        url = reverse("lexicalunit-list")
        payload = {
            "lemma": "unique_test",
            "language": "es",
            "part_of_speech": PartOfSpeech.VERB,
        }
        response1 = authenticated_client.post(url, payload, format="json")
        assert response1.status_code == 201

        # Attempt to create the exact same LU for the same user should fail
        response2 = authenticated_client.post(url, payload, format="json")
        assert response2.status_code == 400

    def test_create_duplicate_lexical_unit_for_different_user_succeeds(
        self, authenticated_client, user_factory
    ):
        url = reverse("lexicalunit-list")
        payload = {
            "lemma": "shared_lemma",
            "language": "fr",
            "part_of_speech": PartOfSpeech.NOUN,
        }
        # The 'authenticated_client' is logged in as the default user
        response1 = authenticated_client.post(url, payload, format="json")
        assert response1.status_code == 201

        # Create and authenticate as a second user
        other_user = user_factory(username="otheruser")
        authenticated_client.force_authenticate(user=other_user)

        # Second user creates the same LU, which should succeed
        response2 = authenticated_client.post(url, payload, format="json")
        assert response2.status_code == 201
        assert LexicalUnit.objects.filter(lemma="shared_lemma").count() == 2

    def test_get_lexical_unit_list_returns_only_own_units(
        self, authenticated_client, lexical_unit_factory, user_factory, default_user
    ):
        url = reverse("lexicalunit-list")
        # Create a unit for our main user (this uses the default_user via the factory)
        lexical_unit_factory(
            lemma="my_apple", language="en", part_of_speech=PartOfSpeech.NOUN
        )

        # Create a unit for another user
        other_user = user_factory(username="otheruser")
        lexical_unit_factory(
            lemma="their_orange",
            language="en",
            part_of_speech=PartOfSpeech.NOUN,
            user=other_user,
        )

        # The API client is authenticated as the default_user
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert len(response.data) == 1  # Should only see 1 unit
        assert response.data[0]["lemma"] == "my_apple"

    def test_update_fails_for_non_owner(
        self, authenticated_client, lexical_unit_factory, user_factory
    ):
        other_user = user_factory(username="otheruser")
        lu_other = lexical_unit_factory(
            lemma="theirs",
            language="en",
            part_of_speech=PartOfSpeech.NOUN,
            user=other_user,
        )

        update_url = reverse("lexicalunit-detail", args=[lu_other.id])
        payload = {"notes": "hacked"}

        # The authenticated_client (as default_user) tries to update another user's object
        response = authenticated_client.patch(update_url, payload, format="json")
        # The get_queryset override should prevent finding this object, resulting in a 404
        assert response.status_code == 404

    def test_delete_fails_for_non_owner(
        self, authenticated_client, lexical_unit_factory, user_factory
    ):
        other_user = user_factory(username="otheruser")
        lu_other = lexical_unit_factory(
            lemma="theirs",
            language="en",
            part_of_speech=PartOfSpeech.NOUN,
            user=other_user,
        )

        delete_url = reverse("lexicalunit-detail", args=[lu_other.id])

        # The authenticated_client (as default_user) tries to delete another user's object
        response = authenticated_client.delete(delete_url)
        assert response.status_code == 404
        assert LexicalUnit.objects.filter(
            id=lu_other.id
        ).exists()  # Should not be deleted
