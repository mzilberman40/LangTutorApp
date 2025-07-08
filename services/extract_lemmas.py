import logging
from typing import List, Optional
from abc import ABC, abstractmethod
import spacy
from langcodes import Language
from pydantic import BaseModel, Field

from ai.answer_with_llm import answer_with_llm
from ai.get_prompt import get_templated_messages

logger = logging.getLogger(__name__)

# --- Configuration for SpaCy models ---
# Map BCP47 language codes (or primary language codes) to SpaCy model names.
# Add more languages as needed, and ensure their models are downloaded.
# e.g., python -m spacy download en_core_web_sm
#       python -m spacy download ru_core_web_sm
#       python -m spacy download de_core_news_sm
# For testing, 'xx_ent_wiki_sm' can be used if a specific language model isn't downloaded,
# but it's not designed for high-quality lemmatization.
SPACY_MODELS = {
    "en": "en_core_web_sm",
    "ru": "ru_core_news_sm",
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",  # Добавляем модель для французского
    "es": "es_core_news_sm",  # Добавляем модель для испанского
    "it": "it_core_news_sm",  # Добавляем модель для итальянского
    "pt": "pt_core_news_sm",  # Добавляем модель для португальского
    "nl": "nl_core_news_sm",  # Добавляем модель для нидерландского
    # "he": "he_core_news_sm", # SpaCy не имеет официальной "sm" модели для иврита, нужно проверить доступность или использовать LLM
    # Add other languages as you support them
}

# Load SpaCy models globally to avoid reloading on each call
_SPACY_PIPELINES = {}
for lang_code, model_name in SPACY_MODELS.items():
    try:
        _SPACY_PIPELINES[lang_code] = spacy.load(model_name)
        logger.info(f"SpaCy model '{model_name}' loaded for language '{lang_code}'.")
    except OSError:
        logger.warning(
            f"SpaCy model '{model_name}' for language '{lang_code}' not found. "
            "Ensure it's downloaded (e.g., `python -m spacy download {model_name}`). "
            "LLM will be used as fallback for this language."
        )
        _SPACY_PIPELINES[lang_code] = None  # Mark as not available

# LLM for text analysis - choose a capable model
LLM_MODEL = "deepseek-ai/DeepSeek-V3-0324"


# --- Pydantic model for LLM response ---
class ExtractedLemmasResponse(BaseModel):
    lemmas: List[str] = Field(
        ..., description="A list of unique canonical lemmas found in the text."
    )


# --- LLM Prompts ---
_SYSTEM_PROMPT_LEMMA_EXTRACTION_LLM = """
You are an expert linguistic analyst. Your task is to process the given text and extract all unique lexical lemmas.
**Instructions:**
1.  Process the entire provided text.
2.  Identify all unique words and reduce them to their canonical lemma form (e.g., "running", "ran", "runs" -> "run").
3.  Filter out common stop words, punctuation-only strings, numbers, and very common function words (e.g., "the", "a", "is", "of"). Focus on content words.
4.  Return the results as a JSON object with a single key "lemmas" which contains a list of unique lemma strings.
"""

_USER_PROMPT_LEMMA_EXTRACTION_LLM = """
Analyze the following text:
"{text}"
"""


# --- Abstract Base Class for Lemma Extraction ---
class BaseLemmaExtractor(ABC):
    @abstractmethod
    def extract(
        self, text: str, source_language: Optional[str] = None
    ) -> Optional[List[str]]:  # Renamed language_hint to source_language
        """
        Extracts unique lemmas from the given text.
        source_language: An optional BCP47 language code to guide extraction.
        """
        pass


# --- Concrete SpaCy Lemma Extractor ---
class SpaCyLemmaExtractor(BaseLemmaExtractor):
    def extract(
        self, text: str, source_language: Optional[str] = None
    ) -> Optional[List[str]]:  # Renamed language_hint to source_language
        if not source_language:
            logger.warning("SpaCy extractor requires a source language.")
            return None

        # Normalize source_language to primary language code (e.g., 'en-GB' -> 'en')
        primary_lang = Language.get(source_language).language
        nlp = _SPACY_PIPELINES.get(primary_lang)

        if not nlp:
            logger.warning(
                f"No SpaCy model loaded for language '{primary_lang}'. Cannot use SpaCy for lemma extraction."
            )
            return None

        try:
            doc = nlp(text)
            lemmas = set()
            for token in doc:
                # Basic filtering: remove punctuation, spaces, numbers, and short tokens
                if (
                    token.is_alpha
                    and not token.is_stop
                    and len(token.lemma_.strip()) > 1
                ):
                    lemmas.add(token.lemma_.lower())  # Convert to lower for consistency
            return sorted(list(lemmas))
        except Exception as e:
            logger.error(
                f"SpaCy lemma extraction failed for source language '{source_language}': {e}",
                exc_info=True,
            )  # Updated log message
            return None


# --- Concrete LLM Lemma Extractor ---
class LLMLemmaExtractor(BaseLemmaExtractor):
    def __init__(self, client):
        self.client = client

    def extract(
        self, text: str, source_language: Optional[str] = None
    ) -> Optional[List[str]]:  # Renamed language_hint to source_language
        try:
            messages = get_templated_messages(
                system_prompt=_SYSTEM_PROMPT_LEMMA_EXTRACTION_LLM,
                user_prompt=_USER_PROMPT_LEMMA_EXTRACTION_LLM,
                params={"text": text},
            )
            response_str = answer_with_llm(
                client=self.client,
                messages=messages,
                model=LLM_MODEL,
                extra_body={"guided_json": ExtractedLemmasResponse.model_json_schema()},
                prettify=False,
                temperature=0.0,
            )
            validated_response = ExtractedLemmasResponse.model_validate_json(
                response_str
            )
            return validated_response.lemmas
        except Exception as e:
            logger.error(f"LLM lemma extraction failed: {e}", exc_info=True)
            return None


# --- Main function for selecting and running extractor ---
def extract_lemmas_from_text(
    client, text: str, source_language: Optional[str] = None
) -> Optional[List[str]]:  # Renamed language_hint to source_language
    """
    Selects and uses the appropriate lemma extractor (SpaCy or LLM) based on language support.

    Args:
        client: An OpenAI-compatible client (required for LLM fallback).
        text: The text block to analyze.
        source_language: An optional BCP47 language code to prioritize SpaCy model usage.

    Returns:
        A list of unique lemma strings, or None if extraction fails.
    """
    # Attempt to use SpaCy if a source_language is provided and model is loaded
    if source_language:
        spacy_extractor = SpaCyLemmaExtractor()
        lemmas = spacy_extractor.extract(text, source_language)
        if lemmas is not None:  # If SpaCy succeeded (even if it found no lemmas)
            logger.info(
                f"Successfully extracted lemmas using SpaCy for source language '{source_language}'."
            )  # Updated log message
            return lemmas
        else:
            logger.warning(
                f"SpaCy failed or not available for source language '{source_language}'. Falling back to LLM."
            )  # Updated log message

    # Fallback to LLM extractor
    llm_extractor = LLMLemmaExtractor(client)
    # Pass source_language to LLM just in case it uses it internally, though current LLM prompt doesn't explicitly use it.
    lemmas = llm_extractor.extract(text, source_language)
    if lemmas is not None:
        logger.info("Successfully extracted lemmas using LLM.")
        return lemmas
    else:
        logger.error("Both SpaCy and LLM lemma extraction failed.")
        return None
