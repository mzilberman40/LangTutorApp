from dataclasses import dataclass

from environs import Env


@dataclass(frozen=True)
class TgBot:
    token: str  # Токен для доступа к телеграм-боту
    admin_ids: list[int]  # Список id администраторов бота


@dataclass(frozen=True)
class Config:
    tg_bot: TgBot


# Создаем функцию, которая будет читать файл .env и возвращать
# экземпляр класса Config с заполненными полями token и admin_ids
def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        tg_bot=TgBot(
            token=env("BOT_TOKEN"), admin_ids=list(map(int, env.list("ADMIN_IDS")))
        )
    )


if __name__ == "__main__":

    config: Config = load_config()

    # Выводим значения полей экземпляра класса Config на печать,
    # чтобы убедиться, что все данные, получаемые из переменных окружения, доступны
    print("BOT_TOKEN:", config.tg_bot.token)
    print("ADMIN_IDS:", config.tg_bot.admin_ids)
    # print()
    # print('DATABASE:', config.db.database)
    # print('DB_HOST:', config.db.db_host)
    # print('DB_USER:', config.db.db_user)
    # print('DB_PASSWORD:', config.db.db_password)
