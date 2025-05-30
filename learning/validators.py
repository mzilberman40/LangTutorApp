from django.core.validators import RegexValidator

# BCP47 language code validator (simple, practical)
bcp47_validator = RegexValidator(
    regex=r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$",
    message="Language code must be in BCP47 format (e.g., en, en-GB, he-IL)",
)
