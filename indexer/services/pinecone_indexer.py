"""Pinecone indexing service."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)


class PineconeIndexer:
    """Service for indexing embeddings in Pinecone."""

    def __init__(
        self,
        api_key: str = None,
        index_name: str = "ragstral-code-index",
        embed_model: str = "codestral-embed",
    ):
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.index_name = index_name
        self.embed_model = embed_model

        if not self.api_key:
            raise ValueError(
                "PINECONE_API_KEY environment variable or api_key parameter required"
            )

        self.pc = Pinecone(api_key=self.api_key)

    def ensure_index_exists(self, dimension: int) -> None:
        """Ensure Pinecone index exists with correct dimension."""
        existing_indexes = [index.name for index in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        else:
            logger.info(f"Pinecone index {self.index_name} already exists")

    def index_repository(
        self, embeddings_dir: Path, repo_name: str, version: str, repo_url: str
    ) -> None:
        """
        Index repository embeddings in Pinecone.

        Args:
            embeddings_dir: Path to embeddings directory
            repo_name: Repository name
            version: Repository version/tag
        """
        # Load embeddings and metadata
        embeddings_file = embeddings_dir / "embeddings.pkl"
        metadata_file = embeddings_dir / "metadata.json"

        with open(embeddings_file, "rb") as f:
            embeddings = np.load(embeddings_file, allow_pickle=True)

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Ensure index exists
        dimension = embeddings.shape[1]
        self.ensure_index_exists(dimension)

        # Get index
        index = self.pc.Index(self.index_name)

        logger.info(f"Indexing {len(embeddings)} embeddings for {repo_name}:{version}")

        # Prepare vectors for upsert
        vectors = []
        batch_size = 100  # Pinecone batch size limit

        for i, (chunk_id, embedding) in enumerate(
            zip(metadata["chunk_ids"], embeddings)
        ):
            # Create unique vector ID
            vector_id = f"{repo_name}:{version}:{chunk_id}"

            # Get original file path
            file_path = metadata["chunk_to_file"].get(chunk_id, chunk_id)

            # file url is the original file path but with the repo name and version
            file_url = f"{repo_url}/blob/{version}/{file_path}"

            # Prepare metadata for Pinecone
            vector_metadata = {
                "repo_name": repo_name,
                "version": version,
                "chunk_id": chunk_id,
                "original_file": file_url,
                "model": metadata.get("model", self.embed_model),
            }

            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding.tolist(),
                    "metadata": vector_metadata,
                }
            )

            # Upsert in batches
            if len(vectors) >= batch_size:
                index.upsert(vectors=vectors)
                vectors = []

        # Upsert remaining vectors
        if vectors:
            index.upsert(vectors=vectors)

        logger.info(
            f"Successfully indexed {len(metadata['chunk_ids'])} vectors for {repo_name}:{version}"
        )

    def search_similar_code(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        repo_name: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search for similar code chunks.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            repo_name: Optional repository name filter
            version: Optional version filter

        Returns:
            List of similar code chunks with metadata
        """
        index = self.pc.Index(self.index_name)

        # Build filter
        filter_dict = {}
        if repo_name:
            filter_dict["repo_name"] = repo_name
        if version:
            filter_dict["version"] = version

        # Search
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict if filter_dict else None,
        )

        return results.matches

    def delete_repository(self, repo_name: str, version: Optional[str] = None) -> None:
        """
        Delete repository embeddings from Pinecone.

        Args:
            repo_name: Repository name
            version: Optional specific version to delete
        """
        index = self.pc.Index(self.index_name)

        # Build filter
        filter_dict = {"repo_name": repo_name}
        if version:
            filter_dict["version"] = version

        # Delete by filter
        index.delete(filter=filter_dict)

        version_str = f":{version}" if version else ""
        logger.info(f"Deleted vectors for {repo_name}{version_str}")

    def list_indexed_repositories(self) -> List[Dict[str, str]]:
        """
        List all indexed repositories and versions.

        Returns:
            List of dictionaries with repo_name and version
        """
        index = self.pc.Index(self.index_name)

        # Query with empty vector to get metadata (this is a workaround)
        # In production, you might want to maintain a separate metadata store
        try:
            stats = index.describe_index_stats()
            total_vectors = stats.total_vector_count

            if total_vectors == 0:
                return []

            # Sample some vectors to get unique repo/version combinations
            # This is not efficient for large indexes
            sample_results = index.query(
                vector=[0.0] * 1024,  # Use default dimension
                top_k=min(1000, total_vectors),
                include_metadata=True,
            )

            repos = set()
            for match in sample_results.matches:
                metadata = match.metadata
                repos.add((metadata.get("repo_name", ""), metadata.get("version", "")))

            return [{"repo_name": repo, "version": version} for repo, version in repos]

        except Exception as e:
            logger.error(f"Failed to list repositories: {e}")
            return []

    def get_index_stats(self) -> Dict:
        """Get Pinecone index statistics."""
        index = self.pc.Index(self.index_name)
        return index.describe_index_stats()
