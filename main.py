import os
from openai import OpenAI

from ai.answer_with_llm import answer_with_llm

# from ai.nebius_list_models import nebius_list_models
from config.config import Config, load_config
from services.unit2phrases import word2phrases

config: Config = load_config()

# Single instance of a Nebius client
nebius_client = OpenAI(
    base_url="https://api.studio.nebius.ai/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
)


if __name__ == "__main__":
    # List available models
    # nebius_list_models(nebius_client)

    # Generate phrases
    system_prompt = word2phrases(client=nebius_client, word="outshine", cefr="C1")
    print(system_prompt)
