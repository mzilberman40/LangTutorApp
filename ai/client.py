# ai/client.py
import os
from openai import OpenAI


def get_client():
    api_key = os.environ.get("NEBIUS_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ API key is not set in NEBIUS_API_KEY or OPENAI_API_KEY")
    return OpenAI(
        base_url="https://api.studio.nebius.ai/v1/",
        api_key=api_key,
    )
