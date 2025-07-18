from utils.prettify_string import prettify_string


def answer_with_llm(
    messages: list,
    client,
    model,
    max_tokens=512,
    prettify=True,
    temperature=None,
    extra_body: dict = None,
) -> str:

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        extra_body=extra_body,
    )

    if prettify:
        return prettify_string(completion.choices[0].message.content)
    else:
        return completion.choices[0].message.content
