# Пожалуйста, полностью замените содержимое этого файла.
import os
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from learning.enums import LexicalCategory, PartOfSpeech
from learning.models import LexicalUnit, Phrase


@pytest.fixture(autouse=True, scope="session")
def set_env():
    os.environ["NEBIUS_API_KEY"] = "test-dummy"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    def create_user(username="testuser", password="password123"):
        return User.objects.create_user(username=username, password=password)

    return create_user


@pytest.fixture
def default_user(user_factory):
    return user_factory()


@pytest.fixture
def authenticated_client(api_client, default_user):
    api_client.force_authenticate(user=default_user)
    return api_client


@pytest.fixture
def lexical_unit_factory(db, default_user):
    def create_lu(**kwargs):
        kwargs.setdefault("user", default_user)
        kwargs.setdefault("lexical_category", LexicalCategory.SINGLE_WORD)
        kwargs.setdefault("part_of_speech", PartOfSpeech.NOUN)
        return LexicalUnit.objects.create(**kwargs)

    return create_lu


@pytest.fixture
def phrase_factory(db):
    """A factory for creating Phrase instances."""

    def create_phrase(**kwargs):
        kwargs.setdefault("text", "A default test phrase.")
        kwargs.setdefault("language", "en")
        return Phrase.objects.create(**kwargs)

    return create_phrase
