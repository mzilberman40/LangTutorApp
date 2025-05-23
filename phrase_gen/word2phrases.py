from ai.answer_with_llm import answer_with_llm


def word2phrases(client, word: str, cefr="B2", lang1="ru", lang2="en_GB", n=5):
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
