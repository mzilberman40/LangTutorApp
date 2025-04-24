import os
import json
import requests
from typing import List, Dict
from dotenv import load_dotenv
from yandex_lib import load_service_key, get_iam_token

load_dotenv()

YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")


def generate_phrases(word: str, level: str, learning_lang: str, native_lang: str, count: int = 5) -> List[Dict[str, str]]:
    """Generate bilingual phrases using YandexGPT containing the given word."""
    key = load_service_key()
    iam_token = get_iam_token(key)

    prompt = (
        f"Generate {count} natural and frequently used phrases in {learning_lang} that include the word '{word}' "
        f"and are appropriate for CEFR level {level}. For each phrase, provide a translation into {native_lang}. "
        f"Return in the format: PHRASE — TRANSLATION"
    )

    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 300
        },
        "messages": [{"role": "user", "text": prompt}]
    }

    response = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    raw_output = response.json()["result"]["alternatives"][0]["message"]["text"]

    phrases = []
    for line in raw_output.strip().split("\n"):
        if "—" in line:
            phrase, translation = line.split("—", 1)
            phrases.append({
                "word": word.strip(),
                "level": level.strip(),
                "phrase": phrase.strip(" -•–—.").strip(),
                "translation": translation.strip(" -•–—.").strip(),
                "learning_lang": learning_lang.strip(),
                "native_lang": native_lang.strip()
            })

    return phrases


# CLI use
if __name__ == "__main__":
    word = input("Enter the word: ")
    level = input("Enter CEFR level (e.g., A2, B1): ")
    learning_lang = input("Enter the learning language (e.g., British English): ")
    native_lang = input("Enter the native language (e.g., Russian): ")

    results = generate_phrases(word, level, learning_lang, native_lang)
    print(json.dumps(results, indent=2, ensure_ascii=False))
