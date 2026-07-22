from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_URL: str | None = None

    FRONTEND_URL: str
    
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"
    ml_artifacts_dir: str = "ml/artifacts"

    # model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
