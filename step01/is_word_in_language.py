import os
import json
import requests
from dotenv import load_dotenv
from yandex_lib import load_service_key, get_iam_token

load_dotenv()

YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")


def is_word_in_language(word: str, target_language: str) -> bool:
    """Checks if a word is used in the target language via YandexGPT API."""
    try:
        key = load_service_key()
        iam_token = get_iam_token(key)

        prompt = f"Is the word '{word}' used in {target_language}? Answer only YES or NO."

        headers = {
            "Authorization": f"Bearer {iam_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.1,
                "maxTokens": 30
            },
            "messages": [{"role": "user", "text": prompt}]
        }

        res = requests.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion", headers=headers, json=payload)
        res.raise_for_status()
        answer = res.json()["result"]["alternatives"][0]["message"]["text"].strip().upper()
        return answer.startswith("YES")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# CLI use
if __name__ == "__main__":
    word = input("Enter the word to check: ")
    language = input("Check if it's used in which language? ")

    result = is_word_in_language(word, language)
    print(json.dumps({"word": word, "language": language, "used_in_language": result}, indent=2, ensure_ascii=False))
