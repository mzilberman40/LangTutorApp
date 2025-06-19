# In learning/services/translate_lemma.py
import logging
from typing import Optional, List
from pydantic import BaseModel
from learning.enums import PartOfSpeech
from learning.models import LexicalUnit
from ai.answer_with_llm import answer_with_llm
from ai.get_prompt import get_templated_messages

logger = logging.getLogger(__name__)


# Pydantic модели остаются без изменений
class TranslationDetail(BaseModel):
    part_of_speech: PartOfSpeech
    pronunciation: Optional[str] = None


class TranslationResponse(BaseModel):
    translated_lemma: Optional[str] = None
    translation_details: List[TranslationDetail]


# 1. Промпт теперь хранится здесь, а не во внешнем файле
_SYSTEM_PROMPT = """
You are an expert translator. The lemma to translate is "{source_lemma}".
It is primarily used as a {source_pos} in its original language, "{source_language_code}".
Translate this lemma into {target_language_code}.

Provide the most common translation. For this translated lemma, provide all its distinct primary parts of speech and their corresponding most common IPA pronunciations in {target_language_code}.
If the pronunciation of the translation is the same for its multiple parts of speech, you can repeat it.

You MUST respond ONLY with a valid JSON object that conforms to the provided JSON Schema.
For each "part_of_speech" field (for the translation), strictly use one of these exact values if applicable: {pos_enum_values_list}.
If the original lemma cannot be translated or if details for the translation cannot be determined, you can use null for "translated_lemma" or provide an empty "translation_details" list.
If pronunciation cannot be determined for a specific part of speech of the translation, use null for its "pronunciation" field.
Ensure "translation_details" is always a list.
"""


def translate_lemma_with_details(
    client, source_lu: LexicalUnit, target_language_code: str
) -> Optional[TranslationResponse]:
    """
    Calls an LLM to translate a given LexicalUnit and get details for the translation,
    using a Pydantic model for guaranteed JSON structure.
    """
    if not source_lu.part_of_speech:
        logger.warning(
            f"Cannot translate LU {source_lu.id} ('{source_lu.lemma}') because its POS is not specified."
        )
        return None

    try:
        pos_enum_list = ", ".join([pos.value for pos in PartOfSpeech])

        params = {
            "source_lemma": source_lu.lemma,
            "source_pos": source_lu.get_part_of_speech_display(),
            "source_language_code": source_lu.language,
            "target_language_code": target_language_code,
            "pos_enum_values_list": pos_enum_list,
        }

        # 2. Логика чтения файла заменена на использование переменной
        messages = get_templated_messages(
            system_prompt=_SYSTEM_PROMPT, user_prompt="", params=params
        )

        response_str = answer_with_llm(
            client=client,
            messages=messages,
            model="meta-llama/Llama-3.3-70B-Instruct",
            extra_body={"guided_json": TranslationResponse.model_json_schema()},
            prettify=False,
            temperature=0.2,
        )

        return TranslationResponse.model_validate_json(response_str)

    except Exception as e:
        logger.error(
            f"LLM call or parsing failed during translation of '{source_lu.lemma}': {e}",
            exc_info=True,
        )
        return None
