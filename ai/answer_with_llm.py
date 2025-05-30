from utils.prettify_string import prettify_string


def answer_with_llm(
    prompt: str,
    client,
    model,
    system_prompt="You are a helpful assistant",
    max_tokens=512,
    prettify=True,
    temperature=None,
) -> str:

    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    completion = client.chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens, temperature=temperature
    )

    if prettify:
        return prettify_string(completion.choices[0].message.content)
    else:
        return completion.choices[0].message.content
