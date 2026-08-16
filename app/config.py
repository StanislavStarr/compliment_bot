from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения.

    URL для Postgres/Redis/Celery собираются из отдельных компонентов, а не
    хранятся как самостоятельные переменные окружения — иначе они могут
    разойтись с POSTGRES_PASSWORD/POSTGRES_HOST при смене окружения
    (docker-compose переопределяет хосты на service-имена).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    environment: Literal["development", "production"] = "development"

    telegram_bot_token: SecretStr = SecretStr("")
    admin_telegram_id: int | None = None

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "compliment_bot"
    postgres_user: str = "compliment_bot"
    postgres_password: SecretStr = SecretStr("change_me")

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    celery_broker_db: int = 1
    celery_result_backend_db: int = 2

    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    log_level: str = "INFO"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.celery_broker_db}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def celery_result_backend(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.celery_result_backend_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
