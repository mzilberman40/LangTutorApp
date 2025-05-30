import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from rest_framework import status
from learning.models import LexicalUnit

pytestmark = pytest.mark.django_db


def _sample_units():
    en = LexicalUnit.objects.create(lemma="apple", language="en-GB")
    return en, en  # kept for symmetry


def test_cannot_translate_itself():
    en, _ = _sample_units()
    client = APIClient()
    url = reverse("lexicalunittranslation-list")

    response = client.post(
        url,
        {"source_unit": en.id, "target_unit": en.id},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot translate to itself" in str(response.data).lower()


def test_cannot_translate_same_language():
    w1 = LexicalUnit.objects.create(lemma="color", language="en-US")
    w2 = LexicalUnit.objects.create(lemma="colour", language="en-GB")
    client = APIClient()
    url = reverse("lexicalunittranslation-list")

    response = client.post(
        url,
        {"source_unit": w1.id, "target_unit": w2.id},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "different languages" in str(response.data).lower()