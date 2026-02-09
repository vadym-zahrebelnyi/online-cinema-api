from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration management.

    Loads settings from environment variables (or a .env file).
    Validates types and ensures all required configurations are present.

    Attributes:
        APP_NAME: The name of the application.
        API_PREFIX: The global prefix for all API routes (e.g., /api/v1).
        LOGIN_TIME_DAYS: Session/Token validity duration in days.

        POSTGRES_*: Database connection credentials.
        SECRET_KEY_*: Keys for JWT token signing and verification.
        REDIS_*: Redis connection settings.
        STRIPE_*: Keys for Stripe payment gateway integration.
        MINIO_*: Credentials for MinIO (S3-compatible storage) management.
        S3_*: Configuration for object storage (buckets, regions).
        SMTP_*: Email server configuration for sending notifications.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "online-cinema-api"
    API_PREFIX: str = "/api/v1"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    LOGIN_TIME_DAYS: int = 7

    SECRET_KEY_ACCESS: str
    SECRET_KEY_REFRESH: str
    JWT_SIGNING_ALGORITHM: str

    REDIS_HOST: str
    REDIS_PORT: int

    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str

    S3_URL: str
    S3_BUCKET_NAME: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_REGION: str

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str
    EMAILS_FROM_NAME: str

    DOMAIN_NAME: str

    @computed_field
    @property
    def DATABASE_URL(self) -> str:  # noqa
        """
        Construct the asynchronous PostgreSQL connection string.

        Returns:
            str: The full SQLAlchemy connection URL (postgresql+asyncpg://...).
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        """
        Construct the Redis connection URL.

        Returns:
            str: The Redis URL (redis://host:port/0).
        """
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()


def get_settings() -> Settings:
    """
    Singleton accessor for application settings.

    Returns:
        Settings: The loaded configuration instance.
    """
    return settings
