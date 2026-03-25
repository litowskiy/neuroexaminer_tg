from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: str

    # Google Docs URL for Python (optional — leave empty to use GPT-only mode)
    PYTHON_DEV_DOC_URL: str = (
        "https://docs.google.com/document/d/1A1U4ogKRkw9v6iqxDChM2O9A5-ucra8liEE3sT7nsQg/edit?usp=sharing"
    )

    # OpenAI model to use
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Прокси для OpenAI (нужен если сервер в РФ и OpenAI блокирует запросы)
    # Вариант А — сменить эндпоинт (proxyapi.ru / openrouter.ai):
    #   OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
    # Вариант Б — HTTP/SOCKS5 прокси:
    #   OPENAI_PROXY=socks5://user:pass@host:port
    #   OPENAI_PROXY=http://user:pass@host:port
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_PROXY: str = ""


settings = Settings()
