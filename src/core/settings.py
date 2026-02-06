from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "online-cinema-api"
    API_PREFIX: str = "/api/v1"

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str

    # SECRET_KEY_ACCESS: str
    # SECRET_KEY_REFRESH: str
    # JWT_SIGNING_ALGORITHM: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    DOMAIN_NAME: str = "http://127.0.0.1:8000"

    @property
    def DATABASE_URL(self) -> str:  # noqa
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
