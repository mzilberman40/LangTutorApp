import os
import json
import requests
import logging
from typing import List, Dict
from dotenv import load_dotenv
from yandex_lib import load_service_key, get_iam_token

load_dotenv()

YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
MIN_WORDS_IN_PHRASE = 5
MAX_WORDS_IN_PHRASE = 15
PHRASES_PER_WORD = 2

logger = logging.getLogger(__name__)

def is_valid_phrase(phrase: str, word: str) -> bool:
    """Check if the phrase satisfies minimum and maximum word counts and includes the source word."""
    words_in_phrase = phrase.strip().split()
    num_words = len(words_in_phrase)
    return (
        MIN_WORDS_IN_PHRASE <= num_words <= MAX_WORDS_IN_PHRASE
        and word.lower() in phrase.lower()
    )

def generate_phrases(word: str, level: str, learning_lang: str, native_lang: str) -> List[Dict[str, str]]:
    """Generate bilingual phrases using YandexGPT containing the given word."""
    key = load_service_key()
    iam_token = get_iam_token(key)

    prompt = (
        f"Generate exactly {PHRASES_PER_WORD} natural and frequently used phrases in {learning_lang} "
        f"that include the word '{word}'. Each phrase must strictly contain between {MIN_WORDS_IN_PHRASE} and {MAX_WORDS_IN_PHRASE} words. "
        f"All phrases must match CEFR level {level}. "
        f"For each phrase, immediately provide its translation into {native_lang}. "
        f"Return the results strictly in the format: PHRASE — TRANSLATION, without numbering, titles, or extra commentary."
    )

    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.7, "maxTokens": 300},
        "messages": [{"role": "user", "text": prompt}],
    }

    response = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    raw_output = response.json()["result"]["alternatives"][0]["message"]["text"]

    phrases = []
    for line in raw_output.strip().split("\n"):
        if "—" in line:
            phrase, translation = line.split("—", 1)
            phrase_clean = phrase.strip(" -•–—.").strip()

            if is_valid_phrase(phrase_clean, word):
                phrases.append(
                    {
                        "word": word.strip(),
                        "native_lang": native_lang.strip(),
                        "learning_lang": learning_lang.strip(),
                        "level": level.strip(),
                        "phrase_on_learning_lang": phrase_clean,
                        "phrase_on_native_lang": translation.strip(" -•–—.").strip(),
                    }
                )
            else:
                logger.warning(f"Rejected phrase: '{phrase_clean}'")

    return phrases

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    word = input("Enter the word: ")
    level = input("Enter CEFR level (e.g., A2, B1): ")
    learning_lang = input("Enter the learning language (e.g., British English): ")
    native_lang = input("Enter the native language (e.g., Russian): ")

    results = generate_phrases(word, level, learning_lang, native_lang)
    print(json.dumps(results, indent=2, ensure_ascii=False))