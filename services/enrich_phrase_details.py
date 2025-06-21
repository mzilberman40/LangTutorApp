# In new file: services/enrich_phrase_details.py

import logging
from typing import Optional

from pydantic import BaseModel, Field

from ai.answer_with_llm import answer_with_llm
from ai.get_prompt import get_templated_messages
from learning.enums import CEFR, PhraseCategory
from learning.models import Phrase

logger = logging.getLogger(__name__)


# 1. Pydantic-модель для валидации ответа от LLM
class PhraseAnalysisResponse(BaseModel):
    is_valid: bool = Field(
        ..., description="Is the phrase grammatically correct AND natural-sounding?"
    )
    justification: Optional[str] = Field(
        None,
        description="Justification if the phrase is invalid, unnatural, or has a language mismatch.",
    )
    language_code: str = Field(
        ..., description="The detected BCP-47 language code (e.g., en-GB, es)."
    )
    cefr_level: CEFR = Field(..., description="The estimated CEFR level of the phrase.")
    category: PhraseCategory = Field(
        ..., description="The most likely category for the phrase."
    )


# 2. Финальная версия промпта
_SYSTEM_PROMPT = """
You are an expert linguistic analyst and language tutor. Your task is to meticulously analyze the phrase "{text}" which was submitted as being in the language "{language}".

You must perform the following analysis and return ONLY a valid JSON object that conforms to the provided schema.

1.  **language_code**: First, identify the actual language and specific dialect (e.g., en-US, en-GB, pt-BR) of the phrase.
2.  **is_valid**: Determine if the phrase is **both** grammatically correct and sounds natural for the language you identified. It is invalid if it has grammatical errors OR sounds awkward/unnatural.
3.  **justification**:
    - If `is_valid` is `false`, provide a concise explanation of WHAT is wrong (e.g., "Grammar error", "Unnatural phrasing", "Language mismatch").
    - If the user-provided language ("{language}") is a mismatch with the language you detected (e.g., user said 'de', you detected 'es'), your justification MUST note this mismatch.
    - If the user-provided language is generic (e.g., 'en') and you detected a specific dialect (e.g., 'en-AU'), your justification should note this nuance (e.g., "Note: Phrasing is typical of Australian English.").
    - If the phrase is perfectly valid and natural, this field must be `null`.
4.  **cefr_level**: Estimate the CEFR level. It MUST be one of: {cefr_list}.
5.  **category**: Classify the phrase. It MUST be one of: {category_list}.
"""


# 3. Основная сервисная функция
def enrich_phrase_details(client, phrase: Phrase) -> Optional[PhraseAnalysisResponse]:
    """
    Calls an LLM to analyze a phrase and returns structured data about it.

    Args:
        client: An OpenAI-compatible client.
        phrase: The Phrase instance to analyze.

    Returns:
        A Pydantic object with the analysis result, or None on failure.
    """
    try:
        cefr_list = ", ".join([level.value for level in CEFR])
        category_list = ", ".join([cat.value for cat in PhraseCategory])

        params = {
            "text": phrase.text,
            "language": phrase.language,
            "cefr_list": cefr_list,
            "category_list": category_list,
        }

        messages = get_templated_messages(
            system_prompt=_SYSTEM_PROMPT, user_prompt="", params=params
        )

        response_str = answer_with_llm(
            client=client,
            messages=messages,
            model="meta-llama/Llama-3.3-70B-Instruct",  # или ваша основная модель
            extra_body={"guided_json": PhraseAnalysisResponse.model_json_schema()},
            temperature=0.1,
        )

        return PhraseAnalysisResponse.model_validate_json(response_str)

    except Exception as e:
        logger.error(
            f"LLM call or parsing failed during enrichment of phrase '{phrase.text}': {e}",
            exc_info=True,
        )
        return None
