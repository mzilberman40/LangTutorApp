# services/unit2phrases.py
import logging
from typing import List
from pydantic import BaseModel, Field

from ai.answer_with_llm import answer_with_llm
from ai.get_prompt import get_templated_messages
from learning.enums import CEFR

logger = logging.getLogger(__name__)

MODEL = "deepseek-ai/DeepSeek-V3-0324"


class PhrasePair(BaseModel):
    original_phrase: str = Field(
        ..., description="The example phrase in the original language."
    )
    translated_phrase: str = Field(..., description="The translated phrase.")
    cefr: CEFR = Field(..., description="The CEFR level of the original phrase.")


class PhraseListResponse(BaseModel):
    phrases: List[PhrasePair]


_SYSTEM_PROMPT = """
You are a language expert. Your task is to generate example sentences for: "{lemma}"

Generate {n} sentences in {source_language} that:
- Each use "{lemma}" naturally in context
- Match the specified CEFR level ({cefr})

Each sentence must:
1. Use different grammatical structures and vocabulary.
2. Include idiomatic expressions or collocations where appropriate.
3. Vary in tone and style (e.g., formal, conversational, narrative).

Translate each generated sentence into {target_language}. The translation must preserve the exact meaning and tone.

Return ONLY a valid JSON object with a single key "phrases" containing a list of {n} phrase objects.
Each object must have these exact keys: "original_phrase", "translated_phrase", "cefr".
"""


def unit2phrases(
    client,
    lemma: str,
    cefr: str,
    source_language: str,
    target_language: str,
    n: int = 5,
) -> str | None:
    """
    Generates example phrases using an LLM with guided JSON responses.
    Uses standardised 'source_language' and 'target_language' parameters.
    """
    try:
        params = {
            "lemma": lemma,
            "n": n,
            "cefr": cefr,
            "source_language": source_language,
            "target_language": target_language,
        }

        messages = get_templated_messages(
            system_prompt=_SYSTEM_PROMPT, user_prompt="", params=params
        )

        response_str = answer_with_llm(
            client=client,
            messages=messages,
            # model="meta-llama/Llama-3.3-70B-Instruct",
            model=MODEL,
            extra_body={"guided_json": PhraseListResponse.model_json_schema()},
            prettify=False,
            temperature=0.7,
        )

        return response_str

    except Exception as e:
        logger.error(f"Failed to generate phrases for '{lemma}': {e}", exc_info=True)
        return None
