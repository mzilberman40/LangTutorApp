# In a new file: services/translate_lemma.py

import json
import logging
from pathlib import Path
from typing import Dict, Any

from learning.enums import PartOfSpeech
from learning.models import LexicalUnit
from ai.answer_with_llm import answer_with_llm

logger = logging.getLogger(__name__)

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "prompts"
    / "translate_lemma_with_details.txt"
)

LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct"


def translate_lemma_with_details(
    client, source_lu: LexicalUnit, target_language_code: str
) -> Dict[str, Any]:
    """
    Calls an LLM to translate a given LexicalUnit and get details for the translation.

    Args:
        client: An OpenAI-compatible API client.
        source_lu: The specific LexicalUnit instance to translate (must have POS).
        target_language_code: The BCP47 code of the language to translate into.

    Returns:
        A dictionary containing the translated lemma and its details, e.g.,
        {'translated_lemma': '...', 'translation_details': [{'part_of_speech': '...', 'pronunciation': '...'}]},
        or an empty dictionary on failure.
    """
    if not source_lu.part_of_speech:
        logger.warning(
            f"Cannot translate LU {source_lu.id} ('{source_lu.lemma}') because its Part of Speech is not specified."
        )
        return {}

    try:
        prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
        pos_choices_str = ", ".join(
            [choice[0] for choice in PartOfSpeech.choices if choice[0]]
        )

        system_prompt = prompt_template.format(
            source_lemma=source_lu.lemma,
            source_pos=source_lu.part_of_speech,
            source_language_code=source_lu.language,
            target_language_code=target_language_code,
            pos_enum_values_list=pos_choices_str,
        )
    except Exception as e:
        logger.error(
            f"Failed to read/format translate_lemma prompt for LU '{source_lu.lemma}': {e}"
        )
        return {}

    try:
        user_prompt = f"Translate '{source_lu.lemma}' ({source_lu.part_of_speech}) from {source_lu.language} to {target_language_code}."

        response_str = answer_with_llm(
            client=client,
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=LLM_MODEL,  # Using a capable model for translation and structured data
            prettify=False,
            temperature=0.2,  # Slightly higher temp can sometimes yield better translations
        )

        response_data = json.loads(response_str)
        logger.info(
            f"Successfully fetched translation for '{source_lu.lemma}' to '{target_language_code}': {response_data}"
        )
        return response_data

    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to decode JSON from LLM for translation of '{source_lu.lemma}': {e}. Response: {response_str}"
        )
    except Exception as e:
        logger.error(f"LLM call failed during translation of '{source_lu.lemma}': {e}")

    return {}  # Return empty dict on any failure
