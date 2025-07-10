# learning/serializers/base.py
from rest_framework import serializers
from learning.validators import bcp47_validator, supported_language_validator


class LanguageField(serializers.CharField):
    """A reusable field for BCP47 language codes with validation."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 16)
        kwargs.setdefault("validators", [bcp47_validator, supported_language_validator])
        super().__init__(*args, **kwargs)