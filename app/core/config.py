# app/core/config.py
from functools import lru_cache
from typing import Optional, List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator
import json


class Settings(BaseSettings):
    # --- Database settings ---
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/fastapi_db"
    TEST_DATABASE_URL: Optional[str] = None  # Added so Pydantic won't reject it

    # --- JWT Settings ---
    JWT_SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    JWT_REFRESH_SECRET_KEY: str = "your-refresh-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Security ---
    BCRYPT_ROUNDS: int = 12

    # --- CORS ---
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """
        Allow CORS_ORIGINS to be provided as a JSON string or comma-separated string.
        """
        if isinstance(v, str):
            try:
                # Try to parse as JSON list
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback: comma-separated
                return [i.strip() for i in v.split(",")]
        return v

    # --- Redis (optional) ---
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create a global settings instance
settings = Settings()


# Optional: Cached getter
@lru_cache()
def get_settings() -> Settings:
    return Settings()
