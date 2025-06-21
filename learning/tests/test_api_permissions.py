# Пожалуйста, полностью замените содержимое этого файла.
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

PROTECTED_URLS = [
    ("get", "lexicalunit-list", {}),
    ("post", "lexicalunit-list", {}),
    ("get", "lexicalunit-detail", {"pk": 0}),  # pk will be replaced
    ("put", "lexicalunit-detail", {"pk": 0}),
    ("patch", "lexicalunit-detail", {"pk": 0}),
    ("delete", "lexicalunit-detail", {"pk": 0}),
    ("post", "lexicalunit-enrich-details", {"pk": 0}),
    ("post", "lexicalunit-translate", {"pk": 0}),
    ("post", "lexicalunit-generate-phrases-for-unit", {"pk": 0}),
    ("get", "lexicalunittranslation-list", {}),
    ("post", "lexicalunittranslation-list", {}),
    ("post", "lexicalunittranslation-bulk-create", {}),
    ("get", "lexicalunittranslation-detail", {"pk": 0}),
]


@pytest.mark.parametrize("method, url_name, kwargs", PROTECTED_URLS)
def test_endpoints_require_authentication(
    api_client, lexical_unit_factory, method, url_name, kwargs
):
    final_kwargs = kwargs.copy()
    if "pk" in final_kwargs:
        lu = lexical_unit_factory(lemma="dummy")
        final_kwargs["pk"] = lu.pk

    url = reverse(url_name, kwargs=final_kwargs)
    http_method = getattr(api_client, method)
    response = http_method(url, data={}, format="json")
    assert response.status_code in [401, 403], f"URL '{url_name}' should be protected"


def test_resolve_lemma_requires_authentication(api_client):
    url = reverse("resolve-lemma")
    payload = {"lemma": "test", "language": "en"}
    response = api_client.post(url, payload, format="json")
    assert response.status_code in [401, 403]


def test_resolve_lemma_is_accessible_for_authenticated_user(authenticated_client):
    url = reverse("resolve-lemma")
    payload = {"lemma": "test", "language": "en"}
    response = authenticated_client.post(url, payload, format="json")
    assert response.status_code == 202
