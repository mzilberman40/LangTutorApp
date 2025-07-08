from pathlib import Path

from ai.answer_with_llm_old import answer_with_llm

PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "phrase2cefr.txt"


def phrase2cefr(phrase: str, language: str, client, model="gpt-3.5-turbo") -> str:
    """
    Estimate the CEFR level of a given phrase in a specific language.

    Args:
        phrase (str): The phrase to classify.
        language (str): The language of the phrase (e.g., "en", "ru").
        client: OpenAI-compatible client.
        model (str): Model to use (default: gpt-3.5-turbo)

    Returns:
        str: CEFR code ("A1" to "C2")
    """
    prompt_template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    prompt = prompt_template.format(language=language, phrase=phrase)

    response = answer_with_llm(
        prompt=prompt,
        client=client,
        model=model,
        system_prompt="You are a CEFR estimation assistant.",
        max_tokens=10,
        prettify=True,
        temperature=0,
    )
    return response.strip()
