# In learning/services/verify_translation.py

import logging
from pydantic import BaseModel, Field
from typing import Optional

from ai.answer_with_llm import answer_with_llm
from ai.get_prompt import get_templated_messages
from learning.models import LexicalUnit

logger = logging.getLogger(__name__)


# 1. Определяем Pydantic модель для структуры ответа LLM
class TranslationQualityResponse(BaseModel):
    quality_score: int = Field(
        ..., description="An integer score from 1 to 5.", ge=1, le=5
    )
    justification: str = Field(..., description="A brief justification for the score.")


# 2. Определяем промпты
_SYSTEM_PROMPT = (
    "You are a translation quality evaluator. You will be given a source word "
    "and its proposed translation. Your task is to rate the translation quality on a scale "
    "from 1 to 5 (1=completely wrong, 3=acceptable, 5=perfect) "
    "and provide a brief justification. You MUST respond with a valid JSON object that "
    "conforms to the provided JSON Schema."
)

_USER_PROMPT = (
    "Evaluate the translation of the {source_language} word '{source_lemma}' "
    "({source_pos}) into {target_language} as '{target_lemma}'."
)


# 3. Создаем основную сервисную функцию
def get_translation_verification(
    client, source_unit: LexicalUnit, target_unit: LexicalUnit
) -> Optional[TranslationQualityResponse]:
    """
    Calls an LLM to verify the quality of a translation between two lexical units.

    Args:
        client: An OpenAI-compatible client.
        source_unit: The source LexicalUnit instance.
        target_unit: The target LexicalUnit instance.

    Returns:
        A Pydantic object with the verification result, or None on failure.
    """
    params = {
        "source_language": source_unit.language,
        "source_lemma": source_unit.lemma,
        "source_pos": source_unit.part_of_speech,
        "target_language": target_unit.language,
        "target_lemma": target_unit.lemma,
    }

    try:
        messages = get_templated_messages(_SYSTEM_PROMPT, _USER_PROMPT, params)

        response_str = answer_with_llm(
            client=client,
            messages=messages,
            model="meta-llama/Llama-3.3-70B-Instruct",
            extra_body={"guided_json": TranslationQualityResponse.model_json_schema()},
            prettify=False,
        )

        return TranslationQualityResponse.model_validate_json(response_str)

    except Exception as e:
        logger.error(
            f"LLM call for translation verification failed: {e}", exc_info=True
        )
        return None
