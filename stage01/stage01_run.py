import json
from dotenv import load_dotenv
from is_word_in_language import is_word_in_language
from phrase_generator import generate_phrases
from stage01.clean_and_validate_input import clean_and_validate_input

load_dotenv()


def step01_pipeline(user_input: dict):
    validated = clean_and_validate_input(user_input)
    words = validated["words"]
    native_lang = validated["native_lang"]
    learning_lang = validated["learning_lang"]
    level = validated["level"]

    result = []
    print(f"✅ Validated & cleaned words: {words}")

    for word in words:
        if is_word_in_language(word, learning_lang):
            print(f"✅ '{word}' accepted in {learning_lang}")
            phrases = generate_phrases(word, level, learning_lang, native_lang)
            result.extend(phrases)
        else:
            print(f"⛔ '{word}' rejected (not in {learning_lang})")
    return result


if __name__ == "__main__":
    words_input = input("Enter comma-separated words: ")
    native_lang = input("Enter native language (e.g., Russian): ")
    learning_lang = input("Enter learning language (e.g., British English): ")
    level = input("Enter CEFR level (e.g., B1): ")

    words = [w.strip() for w in words_input.split(",")]
    user_input = {
        "words": words,
        "native_lang": native_lang,
        "learning_lang": learning_lang,
        "level": level,
    }

    data = step01_pipeline(user_input)

    print("\n🎯 Final Output:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
