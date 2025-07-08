# ai/client.py
import os
from openai import OpenAI

from config.config import Config, load_config

config: Config = load_config()


def get_client():
    # api_key = os.environ.get("NEBIUS_API_KEY") or os.environ.get("OPENAI_API_KEY")
    api_key = config.openai.nebius_key

    if not api_key:
        raise RuntimeError("❌ API key is not set in NEBIUS_API_KEY or OPENAI_API_KEY")
    return OpenAI(
        base_url="https://api.studio.nebius.ai/v1/",
        api_key=api_key,
    )
