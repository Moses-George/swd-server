from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_URL: str | None = None

    FRONTEND_URL: Optional[str]
    
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080,https://smart-water-distribution-web.vercel.app"
    ml_artifacts_dir: Path = Path("/tmp/ml_artifacts") if os.environ.get("VERCEL") else Path(__file__).parent / "artifacts"

    # model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
