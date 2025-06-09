# In learning/utils.py
import re


def get_canonical_lemma(lemma_value: str) -> str:
    """
    Canonicalizes a lemma string:
    1. Strips leading/trailing whitespace.
    2. Replaces internal sequences of whitespace with a single standard space.
    3. Converts to lowercase.
    Returns an empty string if the input is None or results in an empty string.
    """
    if not isinstance(lemma_value, str):
        # Or you might choose to raise an error if None is not expected,
        # but for canonicalization, returning "" for None input is often safe.
        return ""

    stripped_lemma = lemma_value.strip()
    # Replace any sequence of one or more whitespace characters with a single space
    normalized_spacing_lemma = re.sub(r"\s+", " ", stripped_lemma)
    return normalized_spacing_lemma.lower()
