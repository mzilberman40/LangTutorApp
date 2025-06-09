# In services/get_lemma_details.py

import json
import logging
from pathlib import Path
from typing import List, Dict

from learning.enums import PartOfSpeech
from learning.models import LexicalUnit
from ai.answer_with_llm import (
    answer_with_llm,
)  # Assuming this is the correct import path

logger = logging.getLogger(__name__)
# LLM_MODEL = "gpt-4o"  # More capable model for structured JSON tasks
LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "get_lemma_details.txt"
)


def get_lemma_details(client, lexical_unit: LexicalUnit) -> List[Dict]:
    """
    Calls an LLM to get details (all possible POS and their pronunciations)
    for a given LexicalUnit.

    Args:
        client: An OpenAI-compatible API client.
        lexical_unit: The LexicalUnit instance to enrich.

    Returns:
        A list of dictionaries, where each dictionary represents a POS variant
        (e.g., [{'part_of_speech': 'noun', 'pronunciation': '/.../'}]),
        or an empty list if no details are found or an error occurs.
    """
    try:
        prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
        pos_choices_str = ", ".join(
            [choice[0] for choice in PartOfSpeech.choices if choice[0]]
        )

        # The system prompt now only contains the general instructions and the valid POS choices.
        system_prompt = prompt_template.format(pos_enum_values_list=pos_choices_str)

        # The user prompt contains the specific data to be analyzed for this one request.
        user_prompt = f'The lexical unit is: "{lexical_unit.lemma}"\nIts language code is: "{lexical_unit.language}"'

    except Exception as e:
        logger.error(
            f"Failed to read or format get_lemma_details prompt for LU '{lexical_unit.lemma}': {e}"
        )
        return []

    try:
        response_str = answer_with_llm(
            client=client,
            prompt=user_prompt,  # <<< DATA to be processed is here
            system_prompt=system_prompt,  # <<< INSTRUCTIONS are here
            model=LLM_MODEL,
            prettify=False,
            temperature=0.0,  # Low temperature for deterministic structured output
        )

        response_data = json.loads(response_str)
        logger.debug(response_data)
        details_list = response_data.get("lemma_details", [])

        if not isinstance(details_list, list):
            logger.warning(
                f"LLM response for '{lexical_unit.lemma}' details was not a list: {details_list}"
            )
            return []

        logger.info(
            f"Successfully fetched details for '{lexical_unit.lemma}': {details_list}"
        )
        return details_list

    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to decode JSON from LLM for '{lexical_unit.lemma}' details: {e}. Response: {response_str}"
        )
    except Exception as e:
        logger.error(
            f"LLM call failed during get_lemma_details for '{lexical_unit.lemma}': {e}"
        )

    return []  # Return empty list on any other failure
