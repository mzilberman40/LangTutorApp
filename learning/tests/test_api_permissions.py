# In learning/tests/test_api_permissions.py
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

# List of all URL names that should be protected, along with the HTTP method
# and any arguments needed to generate the URL.
PROTECTED_URLS = [
    ("get", "lexicalunit-list", {}),
    ("post", "lexicalunit-list", {}),
    ("get", "lexicalunit-detail", {"pk": 1}),
    ("put", "lexicalunit-detail", {"pk": 1}),
    ("patch", "lexicalunit-detail", {"pk": 1}),
    ("delete", "lexicalunit-detail", {"pk": 1}),
    ("post", "lexicalunit-enrich-details", {"pk": 1}),
    ("post", "lexicalunit-translate", {"pk": 1}),
    ("post", "lexicalunit-generate-phrases-for-unit", {"pk": 1}),
    ("get", "lexicalunittranslation-list", {}),
    ("post", "lexicalunittranslation-list", {}),
    ("post", "lexicalunittranslation-bulk-create", {}),
    ("get", "lexicalunittranslation-detail", {"pk": 1}),
]


@pytest.mark.parametrize("method, url_name, kwargs", PROTECTED_URLS)
def test_endpoints_require_authentication(
    api_client, lexical_unit_factory, method, url_name, kwargs
):
    """
    Verifies that all critical endpoints return 401 Unauthorized
    when accessed by an unauthenticated client.
    """
    # Create a dummy object so that detail URLs (e.g., /lexical-units/1/) are valid.
    # We use the factory, but we don't need the returned object itself.
    if "pk" in kwargs:
        lexical_unit_factory(id=1)

    # Generate the URL for the current test case
    url = reverse(url_name, kwargs=kwargs)

    # Get the corresponding method from the API client (e.g., client.get, client.post)
    http_method = getattr(api_client, method)

    # Make the unauthenticated request
    response = http_method(url, data={}, format="json")

    # Assert that the API correctly denied access
    assert response.status_code in [401, 403], f"URL '{url_name}' should be protected"


def test_resolve_lemma_requires_authentication(api_client):
    """
    Проверяет, что эндпоинт resolve-lemma ЗАЩИЩЕН и возвращает 403
    для неаутентифицированных пользователей.
    """
    url = reverse("resolve-lemma")
    payload = {"lemma": "test", "language": "en"}
    response = api_client.post(url, payload, format="json")
    # Ожидаем, что доступ будет запрещен, так как это правильное поведение
    assert response.status_code == 403


def test_resolve_lemma_is_accessible_for_authenticated_user(authenticated_client):
    """
    Проверяет, что эндпоинт resolve-lemma ДОСТУПЕН для
    аутентифицированных пользователей.
    """
    url = reverse("resolve-lemma")
    payload = {"lemma": "test", "language": "en"}
    response = authenticated_client.post(url, payload, format="json")
    # Для аутентифицированного пользователя мы ожидаем успешного запуска задачи
    assert response.status_code == 202
