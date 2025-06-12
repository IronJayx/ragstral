"""RAG indexing pipeline for GitHub repositories."""

from .pipeline import IndexingPipeline
from .config import get_settings
from .services.github_fetcher import GitHubFetcher
from .services.code_preprocessor import CodeProcessor
from .services.embedding_service import EmbeddingService
from .services.pinecone_indexer import PineconeIndexer

__version__ = "0.1.0"

__all__ = [
    "IndexingPipeline",
    "get_settings",
    "GitHubFetcher",
    "CodeProcessor",
    "EmbeddingService",
    "PineconeIndexer",
]
