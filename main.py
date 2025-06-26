import logging
import os

import django

# Setup Django before importing models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "langs2brain.settings")
django.setup()
from django.conf import settings
import logging.config

logging.config.dictConfig(settings.LOGGING)
from openai import OpenAI

# from ai.answer_with_llm_old import answer_with_llm

from ai.nebius_list_models import nebius_list_models
from config.config import Config, load_config

from learning.models import LexicalUnit
from services.get_lemma_details import get_lemma_details


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

config: Config = load_config()


# Single instance of a Nebius client
nebius_client = OpenAI(
    base_url="https://api.studio.nebius.ai/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
)

if __name__ == "__main__":

    # List available models
    nebius_list_models(nebius_client)

    # Example usage of get_lemma_details

    # lu = LexicalUnit.objects.first()
    # print(lu)
    # result = get_lemma_details(client=nebius_client, lexical_unit=lu)
    # print(result)

    # Generate phrases
    # system_prompt = word2phrases(client=nebius_client, word="outshine", cefr="C1")
    # print(system_prompt)
