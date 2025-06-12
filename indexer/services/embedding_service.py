"""Embedding computation service using Mistral API.

Note: most of the code here comes from https://github.com/mistralai/mistral-embeddings-python/blob/main/mistral_embeddings/embedding_service.py
"""

import json
import logging
import pickle
import os
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from tqdm import tqdm
from mistralai import Mistral
from huggingface_hub import hf_hub_download
from mistral_common.tokens.tokenizers.tekken import Tekkenizer
import time

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for computing embeddings using Mistral API."""

    def __init__(
        self,
        api_key: str = None,
        embed_model: str = "codestral-embed",
        max_batch_size: int = 256,
        max_total_tokens: int = 16384,
        max_sequence_length: int = 8192,
    ):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.embed_model = embed_model
        self.max_batch_size = max_batch_size
        self.max_total_tokens = max_total_tokens
        self.max_sequence_length = max_sequence_length

        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY environment variable or api_key parameter required"
            )

        self.client = Mistral(api_key=self.api_key)
        self.tokenizer = self._init_tokenizer()

    def _init_tokenizer(self) -> Tekkenizer:
        """Initialize the Mistral tokenizer."""
        try:
            repo_id = "mistralai/Mistral-Small-3.1-24B-Base-2503"
            tk_path = hf_hub_download(repo_id, filename="tekken.json")
            return Tekkenizer.from_file(tk_path)
        except Exception as e:
            logger.warning(f"Failed to initialize tokenizer: {e}")
            return None

    def run(self, input_dir: Path, output_dir: Path) -> bool:
        """
        Compute embeddings for preprocessed chunks.

        Args:
            input_dir: Path to the preprocessed directory
            output_dir: Path to the embeddings directory

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"\nComputing embeddings for {input_dir.name}...")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Check if already computed
        embeddings_file = output_dir / "embeddings.pkl"
        metadata_file = output_dir / "metadata.json"

        if embeddings_file.exists() and metadata_file.exists():
            logger.info(f"Embeddings already computed for {input_dir.name}")
            return True

        # Load chunks
        chunks_file = input_dir / "chunks.json"
        if not chunks_file.exists():
            logger.error(f"No chunks file found at {chunks_file}")
            return False

        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        if not chunks:
            logger.error(f"No chunks found for {input_dir.name}")
            return False

        # Prepare texts for embedding
        texts_to_embed = []
        chunk_ids = []
        chunk_to_file = {}

        logger.info("Preparing texts for embedding...")
        for chunk_id, chunk_doc in chunks.items():
            text = self._format_doc(chunk_doc)
            texts_to_embed.append(text)
            chunk_ids.append(chunk_id)

            # Extract original file path from chunk_id
            if "_<chunk>_" in chunk_id:
                original_file = chunk_id.split("_<chunk>_")[0]
            else:
                original_file = chunk_id
            chunk_to_file[chunk_id] = original_file

        # Get embeddings in batches
        print("Getting embeddings...")
        all_embeddings = self._get_embeddings_batch(texts_to_embed)

        if not all_embeddings or len(all_embeddings) != len(texts_to_embed):
            print(f"Error computing embeddings for {input_dir}")
            return False

        # Convert to numpy array
        print("Processing embeddings...")
        embeddings_array = np.array(all_embeddings, dtype=np.float32)

        # Save embeddings
        with open(embeddings_file, "wb") as f:
            pickle.dump(embeddings_array, f)

        # Save metadata
        metadata = {
            "chunk_ids": chunk_ids,
            "chunk_to_file": chunk_to_file,
            "num_chunks": len(chunk_ids),
            "embedding_dimension": embeddings_array.shape[1],
            "model": self.embed_model,
        }

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(
            f"Saved embeddings for {input_dir.name} with {len(chunk_ids)} chunks (dimension: {embeddings_array.shape[1]})"
        )

        return True

    def _format_doc(self, doc: Dict[str, str]) -> str:
        """Format document for embedding."""
        title = doc.get("title", "").strip()
        text = doc.get("text", "").strip()
        return f"{title}\n{text}" if title else text

    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts using Mistral API with token limits."""
        if not texts:
            return []

        # Filter texts by token count and prepare batches
        valid_texts = []
        for text in texts:
            if self.tokenizer:
                tokens = self.tokenizer.encode(text, bos=False, eos=False)
                if len(tokens) <= self.max_sequence_length:
                    valid_texts.append(text)
                else:
                    # Truncate text instead of skipping
                    truncated_tokens = tokens[: self.max_sequence_length]
                    truncated_text = self.tokenizer.decode(truncated_tokens)
                    valid_texts.append(truncated_text)
                    logger.warning(
                        f"Truncated text from {len(tokens)} to {len(truncated_tokens)} tokens"
                    )
            else:
                # If no tokenizer, just use the text as-is (less optimal)
                valid_texts.append(text)

        if not valid_texts:
            return []

        # Create batches respecting token and size limits
        batches = []
        current_batch = []
        current_batch_tokens = 0

        for text in valid_texts:
            if self.tokenizer:
                tokens = self.tokenizer.encode(text, bos=False, eos=False)
                text_token_count = len(tokens)
            else:
                # Rough estimate if no tokenizer
                text_token_count = len(text.split()) * 1.3

            # Check if adding this text would exceed limits
            if (
                len(current_batch) >= self.max_batch_size
                or current_batch_tokens + text_token_count > self.max_total_tokens
            ):
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_batch_tokens = 0

            current_batch.append(text)
            current_batch_tokens += text_token_count

        # Add the last batch if it's not empty
        if current_batch:
            batches.append(current_batch)

        # Process batches - return False immediately if any batch fails
        all_embeddings = []
        for batch in tqdm(batches, desc="Processing embedding batches"):
            try:
                response = self.client.embeddings.create(
                    model=self.embed_model,
                    inputs=batch,
                )
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)

                # Add a small delay between batches to avoid rate limiting
                time.sleep(4)

            except Exception as e:
                logger.error(f"Error getting embeddings for batch: {e}")
                # Return empty list immediately on batch failure
                return []

        return all_embeddings

    def load_embeddings(self, embeddings_dir: Path) -> Tuple[np.ndarray, Dict]:
        """
        Load embeddings and metadata from disk.

        Args:
            embeddings_dir: Path to embeddings directory

        Returns:
            Tuple of (embeddings_array, metadata)
        """
        embeddings_file = embeddings_dir / "embeddings.pkl"
        metadata_file = embeddings_dir / "metadata.json"

        with open(embeddings_file, "rb") as f:
            embeddings = pickle.load(f)

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return embeddings, metadata
