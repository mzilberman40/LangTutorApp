from pathlib import Path

from ai.answer_with_llm import answer_with_llm
from ai.client import get_client

import logging

logger = logging.getLogger(__name__)
client = get_client()

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "unit2phrase.txt"


def unit2phrases(client, lemma: str, cefr="B2", lang1="ru", lang2="en-GB", n=5) -> str:
    """
    Generate phrases using an LLM for a given word.

    Returns:
        Raw LLM response (JSON string expected to be parsed elsewhere).
    """
    try:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8").format(
            lemma=lemma, n=n, cefr=cefr, lang1=lang1, lang2=lang2
        )
    except Exception as e:
        logger.error(f"Failed to read or format prompt file: {e}")
        raise

    try:
        response = answer_with_llm(
            prompt=lemma,
            system_prompt=system_prompt,
            model="meta-llama/Llama-3.3-70B-Instruct",
            prettify=False,
            client=client,
        )
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise

    return response
