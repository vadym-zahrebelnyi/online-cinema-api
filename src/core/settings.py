from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "online-cinema-api"
    API_PREFIX: str = "/api/v1"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "test_cinema"

    LOGIN_TIME_DAYS: int = 7

    SECRET_KEY_ACCESS: str = "test_access_secret"
    SECRET_KEY_REFRESH: str = "test_refresh_secret"
    JWT_SIGNING_ALGORITHM: str = "HS256"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    STRIPE_SECRET_KEY: str = "sk_test_123"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_123"
    STRIPE_WEBHOOK_SECRET: str = "whsec_test_123"

    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    S3_URL: str = "http://localhost:9000"
    S3_BUCKET_NAME: str = "test-bucket"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_REGION: str = "us-east-1"

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str = "info@example.com"
    EMAILS_FROM_NAME: str = "OnlineCinema"

    DOMAIN_NAME: str = "http://127.0.0.1:8000"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:  # noqa
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()


def get_settings() -> Settings:
    return settings
