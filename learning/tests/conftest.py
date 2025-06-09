import os
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from learning.models import LexicalUnit


@pytest.fixture(autouse=True, scope="session")
def set_env():
    os.environ["NEBIUS_API_KEY"] = "test-dummy"


@pytest.fixture
def api_client():
    """A pytest fixture that provides an unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def user_factory(db):
    """A factory to create user instances."""

    def create_user(username="testuser", password="password123"):
        return User.objects.create_user(username=username, password=password)

    return create_user


@pytest.fixture
def default_user(user_factory):
    """A default, standard user for tests."""
    return user_factory()


@pytest.fixture
def authenticated_client(api_client, default_user):
    """A client that is pre-authenticated with the default user."""
    api_client.force_authenticate(user=default_user)
    return api_client


@pytest.fixture
def lexical_unit_factory(db, default_user):
    """
    A factory for creating LexicalUnit instances, automatically associating
    them with the default user.
    """

    def create_lu(**kwargs):
        # If a user is not specified in the call, use the default user.
        if "user" not in kwargs:
            kwargs["user"] = default_user
        return LexicalUnit.objects.create(**kwargs)

    return create_lu
