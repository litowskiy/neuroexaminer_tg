from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: str

    # Google Docs URLs for each topic
    PYTHON_DEV_DOC_URL: str = (
        "https://docs.google.com/document/d/1A1U4ogKRkw9v6iqxDChM2O9A5-ucra8liEE3sT7nsQg/edit?usp=sharing"
    )
    DATA_ANALYST_DOC_URL: str = ""

    # OpenAI model to use
    OPENAI_MODEL: str = "gpt-3.5-turbo-1106"


settings = Settings()
