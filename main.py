import os
from openai import OpenAI

from ai.answer_with_llm import answer_with_llm
from ai.nebius_list_models import nebius_list_models
from config.config import Config, load_config

config: Config = load_config()

# Single instance of a Nebius client
nebius_client = OpenAI(
    base_url="https://api.studio.nebius.ai/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
)


def word2phrase(client, word: str, cefr="B2", lang1="ru", lang2="en_GB", n=5):
    with open("prompts/word2phrase.txt", "r", encoding="utf8") as f:
        system_prompt = f.read().format(
            word=word, n=n, cefr=cefr, lang1=lang1, lang2=lang2
        )

    prompt = word
    model = "meta-llama/Llama-3.3-70B-Instruct"

    response = answer_with_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        prettify=False,
        client=client,
    )

    return response


if __name__ == "__main__":
    # List available models
    # nebius_list_models(nebius_client)

    # Generate phrases
    system_prompt = word2phrase(client=nebius_client, word="outshine", cefr="C1")
    print(system_prompt)
