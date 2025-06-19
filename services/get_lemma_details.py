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
from learning.enums import PartOfSpeech
from learning.models import LexicalUnit

logger = logging.getLogger(__name__)

LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

# ─────────────────────── Pydantic models ──────────────────────────────


class CharacterProfile(BaseModel):
    """Single POS–pronunciation pair."""

    part_of_speech: PartOfSpeech
    pronunciation: str | None = None


class CharacterProfileResponse(BaseModel):
    """Top-level wrapper required by guided_json."""

    lemma_details: List[CharacterProfile]


# ───────────────────────── Prompt templates ───────────────────────────

_PROMPT_TEMPLATE = """
You are an expert linguistic analyst. Your task is to analyze the lexical unit "{lemma}" within the context of the language "{language}".

**CRITICAL RULE: First, determine if "{lemma}" is a recognized word in the language "{language}". This includes common loanwords. If it is NOT a recognized word, you MUST return an empty list for "lemma_details": {{"lemma_details": []}}. Do not proceed with analysis if the word does not belong to the language.**

If the word is recognized, return JSON that conforms to the supplied schema.
• The field "part_of_speech" **must** be one of: {pos_enum_values_list}.
• If the lexical unit is a proper noun or its POS is outside the list, return an empty list.
• If a pronunciation cannot be determined for an entry, set its value to null.

Respond with nothing except valid JSON.
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
        pos_choices_str = ", ".join(
            choice[0] for choice in PartOfSpeech.choices if choice[0]
        )

        params = {
            "lemma": lexical_unit.lemma,
            "language": lexical_unit.language,
            "pos_enum_values_list": pos_choices_str,
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
