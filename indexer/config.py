"""Configuration settings for the indexing pipeline."""

from pathlib import Path
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Keys
    mistral_api_key: str
    pinecone_api_key: str
    pinecone_environment: str

    # Model Configuration
    embed_model: str = "codestral-embed"
    chunk_size: int = 3000
    chunk_overlap: int = 1000
    max_batch_size: int = 128
    max_total_tokens: int = 16384
    max_sequence_length: int = 8192

    # Pinecone Configuration
    pinecone_index_name: str = "ragstral-code-index"
    pinecone_dimension: int = 1024

    # Local Storage
    data_dir: Path = Path(__file__).parent / "data"

    class Config:
        env_file = Path(__file__).parent / ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
