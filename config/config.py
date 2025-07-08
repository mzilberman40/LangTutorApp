from dataclasses import dataclass

from environs import Env


@dataclass(frozen=True)
class OpenAI:
    nebius_key: str


@dataclass(frozen=True)
class DJANGO:
    secret_key: str

@dataclass(frozen=True)
class L2B:
    api_key: str


# L2B_IMPORT_API_KEY = env.str("L2B_IMPORT_API_KEY", default=None)

@dataclass(frozen=True)
class Config:
    openai: OpenAI
    django: DJANGO
    lang2brain: L2B


# Создаем функцию, которая будет читать файл .env и возвращать
# экземпляр класса Config с заполненными полями token и admin_ids
def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        openai=OpenAI(
            nebius_key=env("NEBIUS_API_KEY"),
        ),
        django=DJANGO(
            secret_key=env("DJANGO_SECRET_KEY")
        ),
        lang2brain=L2B(
            api_key=env("L2B_IMPORT_API_KEY"),
        )
    )


if __name__ == "__main__":

    config: Config = load_config()

    # Выводим значения полей экземпляра класса Config на печать,
    # чтобы убедиться, что все данные, получаемые из переменных окружения, доступны
    print("NEBIUS_API_KEY:", config.openai.nebius_key)
