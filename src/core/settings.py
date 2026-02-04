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

    REDIS_HOST: str
    REDIS_PORT: int
    DATABASE_URL: str

settings = Settings()
