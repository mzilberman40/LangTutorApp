import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
# from django.contrib.auth.models import User

from learning.models import LexicalUnit, LexicalUnitTranslation, Phrase, PhraseTranslation
# from learning.enums import LexicalCategory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(user_factory):
    return user_factory(username="importer_user")


@pytest.fixture
def lexical_unit_payload():
    """Provides a valid payload for importing a LEXICAL_UNIT."""
    return {
        "entity_type": "LEXICAL_UNIT",
        "source": {
            "text": "pivotal role",
            "language": "en-GB",
            "part_of_speech": "noun",
            "lexical_category": "IDIOM"
        },
        "targets": [
            {
                "text": "ключевая роль",
                "language": "ru",
                "part_of_speech": "noun",
                "lexical_category": "IDIOM"
            }
        ]
    }


@pytest.fixture
def phrase_payload():
    """Provides a valid payload for importing a PHRASE."""
    return {
        "entity_type": "PHRASE",
        "source": {
            "text": "The early bird gets the worm.",
            "language": "en-US"
        },
        "targets": [
            {
                "text": "Кто рано встает, тому бог подает.",
                "language": "ru"
            }
        ]
    }


def test_import_lexical_unit_success(api_client, test_user, lexical_unit_payload, settings):
    """Tests successful import of a LexicalUnit and the rich response."""
    settings.L2B_IMPORT_API_KEY = "test-key"
    url = reverse('external-import', kwargs={'user_id': test_user.id})
    headers = {'X-API-Key': 'test-key'}

    response = api_client.post(url, data=lexical_unit_payload, format='json', headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['created_entity'] == 'LexicalUnit'
    assert response.data['source']['lemma'] == 'pivotal role'
    assert response.data['source']['user'] == test_user.id
    assert len(response.data['targets']) == 1
    assert response.data['targets'][0]['lemma'] == 'ключевая роль'
    assert LexicalUnit.objects.count() == 2
    assert LexicalUnitTranslation.objects.count() == 1


def test_import_phrase_success(api_client, test_user, phrase_payload, settings):
    """Tests successful import of a standalone Phrase and the rich response."""
    settings.L2B_IMPORT_API_KEY = "test-key"
    url = reverse('external-import', kwargs={'user_id': test_user.id})
    headers = {'X-API-Key': 'test-key'}

    response = api_client.post(url, data=phrase_payload, format='json', headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['created_entity'] == 'Phrase'
    assert response.data['source']['text'] == 'The early bird gets the worm.'
    assert len(response.data['targets']) == 1
    assert response.data['targets'][0]['text'] == 'Кто рано встает, тому бог подает.'
    assert Phrase.objects.count() == 2
    assert PhraseTranslation.objects.count() == 1


def test_import_lexical_unit_missing_required_fields(api_client, test_user, lexical_unit_payload, settings):
    """
    Tests that importing a LEXICAL_UNIT fails if required fields are missing.
    """
    settings.L2B_IMPORT_API_KEY = "test-key"
    url = reverse('external-import', kwargs={'user_id': test_user.id})
    headers = {'X-API-Key': 'test-key'}

    del lexical_unit_payload['source']['part_of_speech']

    response = api_client.post(url, data=lexical_unit_payload, format='json', headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "'part_of_speech' and 'lexical_category' are required" in str(response.data)
