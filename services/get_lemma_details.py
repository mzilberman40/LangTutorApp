"""Langs2Brain – fetch lemma details via LLM.

Queries the LLM for every common part of speech and its IPA pronunciation
for a lexical unit, using guided-JSON that matches the Pydantic schema
(CharacterProfileResponse).  Any response is strictly validated before use.
"""

from __future__ import annotations

import logging
from typing import List

# from openai import OpenAI  # type: ignore
from pydantic import BaseModel

from ai.answer_with_llm import answer_with_llm
from ai.client import get_client
from ai.get_prompt import get_templated_messages
from learning.enums import PartOfSpeech, LexicalCategory
from learning.models import LexicalUnit

logger = logging.getLogger(__name__)

LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

# ─────────────────────── Pydantic models ──────────────────────────────


class CharacterProfile(BaseModel):
    """Single POS–pronunciation pair."""

    lexical_category: LexicalCategory
    part_of_speech: PartOfSpeech
    pronunciation: str | None = None


class CharacterProfileResponse(BaseModel):
    """Top-level wrapper required by guided_json."""

    lemma_details: List[CharacterProfile]


_PROMPT_TEMPLATE = """
You are an expert linguistic analyst. Your task is to analyze the lexical unit "{lemma}" in the language "{language}".

**Analysis Steps:**
1.  **Recognition:** First, determine if "{lemma}" is a recognized word, multi-word unit, idiom, or phrasal verb in the language "{language}". If not, you MUST return an empty list for "lemma_details": {{"lemma_details": []}}.
2.  **Categorization:** For each recognized form, determine its structural type (`lexical_category`) and its primary grammatical function (`part_of_speech`).

**CRITICAL RULES:**
-   `lexical_category` MUST be one of: {lexical_category_enum_list}.
-   `part_of_speech` MUST be one of: {pos_enum_values_list}.
-   For multi-word units (e.g., phrasal verbs, idioms), the `part_of_speech` must reflect the function of the ENTIRE phrase (e.g., "take off" is a 'verb').
-   If the lexical unit is a proper noun or its type/POS is outside the provided lists, return an empty list.
-   If pronunciation cannot be found, set its value to null.

Respond with nothing except valid JSON that conforms to the schema.
""".strip()

_USER_PROMPT = 'The lexical unit is: "{lemma}"\nIts language code is: "{language}"'


# ──────────────────────────── Service ─────────────────────────────────
# client = get_client()


def get_lemma_details(client, lexical_unit: LexicalUnit) -> list[dict]:
    """Return all POS variants and IPA pronunciations for *lexical_unit*.

    Args:
        client: OpenAI-compatible client instance.
        lexical_unit: The lexical unit to enrich.

    Returns:
        A list like:
        `[{"part_of_speech": "noun", "pronunciation": "/tʃæt/"}, …]`.
        An empty list is returned on any error or when nothing is found.
    """
    try:
        # Получаем список частей речи
        pos_choices_str = ", ".join(
            choice[0] for choice in PartOfSpeech.choices if choice[0]
        )
        # +++ Получаем список лексических категорий
        lexical_category_choices_str = ", ".join(
            choice[0] for choice in LexicalCategory.choices if choice[0]
        )
        params = {
            "lemma": lexical_unit.lemma,
            "language": lexical_unit.language,
            "pos_enum_values_list": pos_choices_str,
            "lexical_category_enum_list": lexical_category_choices_str,  # <-- Передаем в промпт
        }
        messages = get_templated_messages(
            system_prompt=_PROMPT_TEMPLATE, user_prompt=_USER_PROMPT, params=params
        )

        response_str = answer_with_llm(
            messages=messages,
            client=client,
            model=LLM_MODEL,
            prettify=False,
            temperature=0.0,
            extra_body={"guided_json": CharacterProfileResponse.model_json_schema()},
        )

        validated = CharacterProfileResponse.model_validate_json(response_str)
        logger.debug("Validated LLM response: %s", validated)

        return [profile.model_dump() for profile in validated.lemma_details]

    except Exception as exc:  # noqa: BLE001  (logged & swallowed)
        logger.error(
            "Fetching details for %s failed: %s",
            lexical_unit.lemma,
            exc,
            exc_info=True,
        )
        return []
