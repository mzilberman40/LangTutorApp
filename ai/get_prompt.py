from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import convert_to_openai_messages


def get_templated_messages(
    system_prompt: str,
    user_prompt: str,
    params: dict = None,
) -> list:
    """
    Returns a list of messages formatted for OpenAI API.
    """
    params = params or {}
    prompt_template = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("user", user_prompt)]
    )
    templated_messages = convert_to_openai_messages(
        prompt_template.invoke(params).to_messages()
    )
    return templated_messages


if __name__ == "__main__":
    messages = get_templated_messages(
        system_prompt="You only {def} answer in rhymes",
        user_prompt="Tell me about {city}",
        params={"city": "Madrid", "def": "good"},
    )
    print(messages)
