from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# BCP47 language code validator (simple, practical)
bcp47_validator = RegexValidator(
    regex=r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$",
    message="Language code must be in BCP47 format (e.g., en, en-GB, he-IL)",
)


def supported_language_validator(value):
    """
    Checks if a given language code is in the project's list of supported languages.
    """
    # Приводим к нижнему регистру для унификации сравнения
    normalized_value = value.lower()
    supported_langs_lower = [lang.lower() for lang in settings.SUPPORTED_LANGUAGES]

    if normalized_value not in supported_langs_lower:
        # Django validators обычно выбрасывают ValidationError
        raise ValidationError(
            f"Language code '{value}' is not supported by this application."
        )
