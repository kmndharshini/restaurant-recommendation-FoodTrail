import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    LLM_PROVIDER: str = "groq"               # "groq" (primary)
    LLM_MODEL: str = "openai/gpt-oss-120b"  # Groq-hosted 120B model (efficient & powerful)
    MAX_CANDIDATES: int = 8                 # Compact candidate pool to stay well within 8K TPM
    MAX_LLM_TOKENS: int = 500               # Strict output token cap for minimum usage
    DATASET_ID: str = "ManikaSaini/zomato-restaurant-recommendation"
    PROCESSED_DATA_PATH: str = "data/processed/restaurants.parquet"
    ALLOWED_ORIGINS: str = "*"              # Comma-separated domains or "*" for all
    PORT: int = 8000                        # Default application port (Railway supplies via env)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
