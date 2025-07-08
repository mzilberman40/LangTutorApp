# learning/permissions.py
from rest_framework import permissions
from django.conf import settings

class HasAPIKey(permissions.BasePermission):
    """
    Allows access only if a valid API key is provided in the request headers.
    The key is expected in the 'X-API-Key' header.
    """
    message = 'Invalid or missing API Key.'

    def has_permission(self, request, view):
        # Get the API key from the request header
        api_key = request.headers.get('X-API-Key')

        # Get the expected API key from Django settings
        expected_key = getattr(settings, 'L2B_IMPORT_API_KEY', None)

        # This check is case-sensitive and whitespace-sensitive.
        if not api_key or not expected_key or api_key != expected_key:
            return False

        return True
