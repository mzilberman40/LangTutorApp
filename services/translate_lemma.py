# In learning/services/translate_lemma.py
import logging
from typing import Optional, List
from pydantic import BaseModel
from learning.enums import PartOfSpeech, LexicalCategory
from learning.models import LexicalUnit
from ai.answer_with_llm import answer_with_llm
from ai.get_prompt import get_templated_messages

logger = logging.getLogger(__name__)


# Pydantic модели остаются без изменений
class TranslationDetail(BaseModel):
    lexical_category: LexicalCategory  # <-- ДОБАВЛЯЕМ
    part_of_speech: PartOfSpeech
    pronunciation: Optional[str] = None


class TranslationResponse(BaseModel):
    translated_lemma: Optional[str] = None
    translation_details: List[TranslationDetail]


_SYSTEM_PROMPT = """
You are an expert translator. The source lexical unit is "{source_lemma}".
It is a {source_lexical_category} and its primary part of speech is {source_pos} in its original language, "{source_language_code}".
Translate this lemma into {target_language_code}.

For the most common translation, provide all its distinct structural types (`lexical_category`) and their corresponding primary parts of speech (`part_of_speech`), along with IPA pronunciations.

**CRITICAL RULES:**
-   `lexical_category` MUST be one of: {lexical_category_enum_list}.
-   `part_of_speech` MUST be one of: {pos_enum_values_list}.
-   You MUST respond ONLY with a valid JSON object.
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
        # +++ Получаем список лексических категорий
        lexical_category_enum_list = ", ".join([cat.value for cat in LexicalCategory])

        params = {
            "source_lemma": source_lu.lemma,
            "source_lexical_category": source_lu.get_lexical_category_display(),  # <-- Добавили для контекста
            "source_pos": source_lu.get_part_of_speech_display(),
            "source_language_code": source_lu.language,
            "target_language_code": target_language_code,
            "pos_enum_values_list": pos_enum_list,
            "lexical_category_enum_list": lexical_category_enum_list,  # <-- Передаем в промпт
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
