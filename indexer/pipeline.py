#!/usr/bin/env python3
"""Simple CLI pipeline for indexing GitHub repositories."""

import argparse
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

from services.github_fetcher import download_repo
from services.code_preprocessor import CodePreprocessor
from services.embedding_service import EmbeddingService
from services.pinecone_indexer import PineconeIndexer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_repo_name(repo_url: str) -> str:
    """Extract repository name from URL."""
    return repo_url.split("/")[-1]


def run_pipeline(repo_url: str, tags: list[str]):
    """Run the indexing pipeline for a repository with given tags."""
    repo_name = extract_repo_name(repo_url)
    data_dir = Path(__file__).parent / "data"

    # Use "latest" if no tags provided
    if not tags:
        tags = ["latest"]

    logger.info(f"Processing repository: {repo_url}")
    logger.info(f"Tags: {tags}")

    # Check for required environment variables
    if not os.getenv("MISTRAL_API_KEY"):
        logger.error("MISTRAL_API_KEY environment variable is required")
        sys.exit(1)

    if not os.getenv("PINECONE_API_KEY"):
        logger.error("PINECONE_API_KEY environment variable is required")
        sys.exit(1)

    # Initialize services
    preprocessor = CodePreprocessor()
    embedding_service = EmbeddingService()
    indexer = PineconeIndexer(
        index_name="ragstral-code-index",
        embed_model="codestral-embed",
    )

    for tag in tags:
        logger.info(f"Processing tag: {tag}")

        # Set up directories
        repo_dir = data_dir / repo_name / tag

        # Set pipeline steps directories
        raw_dir = repo_dir / "stage=raw"
        preprocessed_dir = repo_dir / "stage=preprocessed"
        embeddings_dir = repo_dir / "stage=embeddings"

        # Skip if already exists
        if repo_dir.exists():
            logger.info(
                f"Repository {repo_name}:{tag} already exists, skipping download"
            )
        else:
            # Download repository
            success = download_repo(repo_url, raw_dir, tag if tag != "latest" else None)
            if not success:
                logger.error(f"Failed to download {repo_name}:{tag}")
                return

        try:
            # preprocess code
            logger.info(f"Processing code for {repo_name}:{tag}")
            success = preprocessor.run(raw_dir, preprocessed_dir)
            if not success:
                logger.error(f"Failed to process code for {repo_name}:{tag}")
                return

            # Compute embeddings
            logger.info(f"Computing embeddings for {repo_name}:{tag}")
            success = embedding_service.run(preprocessed_dir, embeddings_dir)
            if not success:
                logger.error(f"Failed to compute embeddings for {repo_name}:{tag}")
                return

            # Index in Pinecone
            logger.info(f"Indexing in Pinecone for {repo_name}:{tag}")
            indexer.index_repository(embeddings_dir, repo_name, tag, repo_url)

            logger.info(f"Successfully completed pipeline for {repo_name}:{tag}")

        except Exception as e:
            logger.error(f"Failed to process {repo_name}:{tag}: {e}")
            return


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Index GitHub repositories for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py https://github.com/user/repo v1.0.0 v1.1.0
        """,
    )

    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("tags", nargs="*", help="Git tags to process (default: latest)")

    args = parser.parse_args()

    try:
        run_pipeline(args.repo_url, args.tags)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
