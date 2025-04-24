import re
from typing import List, Dict, Any

SUPPORTED_LANGUAGES = ["Russian", "British English", "American English", "Hebrew"]
VALID_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

LANGUAGE_ALIASES = {
    "ru": "Russian",
    "russian": "Russian",

    "he": "Hebrew",
    "hebrew": "Hebrew",

    "en": "British English",  # default
    "en-gb": "British English",
    "british": "British English",
    "british english": "British English",

    "en-us": "American English",
    "us": "American English",
    "american": "American English",
    "american english": "American English"
}


def resolve_language(name: str) -> str:
    name = name.strip().lower()
    resolved = LANGUAGE_ALIASES.get(name)
    if not resolved:
        raise ValueError(f"Unsupported language identifier: '{name}'")
    return resolved


def clean_and_validate_input(data: Dict[str, Any]) -> Dict[str, Any]:
    words_raw = data.get("words", [])
    native_lang = resolve_language(data.get("native_lang", "Russian"))
    learning_lang = resolve_language(data.get("learning_lang", "British English"))
    level = data.get("level", "B1").strip().upper()
    N = data.get("N", 5)

    if not isinstance(words_raw, list):
        raise ValueError("`words` must be a list of strings.")
    if not all(isinstance(word, str) for word in words_raw):
        raise ValueError("All items in `words` must be strings.")
    if native_lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"`native_lang` must be one of {SUPPORTED_LANGUAGES}")
    if learning_lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"`learning_lang` must be one of {SUPPORTED_LANGUAGES}")
    if level not in VALID_LEVELS:
        raise ValueError(f"`level` must be one of {VALID_LEVELS}")
    if not isinstance(N, int) or N <= 0:
        raise ValueError("`N` must be a natural number greater than 0.")

    cleaned_words = set()
    for word in words_raw:
        cleaned = re.sub(r'[^\w\s]', '', word).strip().lower()
        if cleaned:
            cleaned_words.add(cleaned)

    return {
        "words": sorted(cleaned_words),
        "native_lang": native_lang,
        "learning_lang": learning_lang,
        "level": level,
        "N": N
    }
