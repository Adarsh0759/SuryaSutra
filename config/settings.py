"""Central runtime config, loaded once from environment / .env (D-16, D-18, D-21)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/processed/suryasutra.db"
    raw_data_dir: Path = Path("./data/raw")
    processed_data_dir: Path = Path("./data/processed")

    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    groq_api_key: str | None = None


settings = Settings()
