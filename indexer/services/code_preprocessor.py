"""Code processing and chunking service.

Note: most of the code here comes from https://github.com/mistralai/mistral-embeddings-python/blob/main/mistral_embeddings/embedding_service.py
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class CodePreprocessor:
    """Service for processing and chunking code files."""

    def __init__(self, chunk_size: int = 3000, chunk_overlap: int = 1000):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def run(self, input_dir: Path, output_dir: Path) -> bool:
        """
        Process a repository by flattening structure and chunking code.

        Args:
            input_dir: Path to the repository directory
            output_dir: Path to the preprocessed directory

        Returns:
            True if successful, False otherwise
        """
        output_dir.mkdir(exist_ok=True)

        # Check if already processed
        corpus_file = output_dir / "corpus.json"
        chunks_file = output_dir / "chunks.json"

        logger.info(f"Processing repository at {input_dir}")

        # Flatten repository structure
        flattened_files = self._flatten_repository(input_dir)

        # Save original corpus
        with open(corpus_file, "w", encoding="utf-8") as f:
            json.dump(flattened_files, f, indent=2, ensure_ascii=False)

        # Create corpus format for chunking
        corpus = {}
        for file_path, content in flattened_files.items():
            corpus[file_path] = {"title": file_path, "text": content}

        # Chunk the corpus
        chunked_corpus = self._chunk_corpus(corpus)

        # Save chunked corpus
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(chunked_corpus, f, indent=2, ensure_ascii=False)

        logger.info(
            f"Processed {len(flattened_files)} files into {len(chunked_corpus)} chunks"
        )

        return True

    def _flatten_repository(self, repo_path: Path) -> Dict[str, str]:
        """
        Flatten repository structure and extract code files.

        Args:
            repo_path: Path to the repository

        Returns:
            Dictionary mapping file paths to their content
        """
        flattened = {}

        # Supported code file extensions
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".cs",
            ".rb",
            ".go",
            ".rs",
            ".php",
            ".swift",
            ".kt",
            ".scala",
            ".r",
            ".m",
            ".mm",
            ".sh",
            ".ps1",
            ".sql",
            ".html",
            ".css",
            ".jsx",
            ".tsx",
            ".vue",
            ".svelte",
        }

        for file_path in repo_path.rglob("*"):
            if (
                file_path.is_file()
                and file_path.suffix.lower() in code_extensions
                and not self._should_skip_file(file_path)
            ):
                try:
                    # Get relative path from repo root
                    relative_path = file_path.relative_to(repo_path)

                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().strip()

                    if content:  # Only keep non-empty files
                        flattened[str(relative_path)] = content

                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")

        return flattened

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped based on file name or extension."""
        skip_patterns = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            ".env",
            ".DS_Store",
        }

        # Skip if the file name or extension matches skip patterns
        file_name = file_path.name.lower()
        for pattern in skip_patterns:
            if pattern in file_name:
                return True

        return False

    def _get_language_from_path(self, path: str) -> Optional[Language]:
        """Get language from file extension."""
        extension_to_language = {
            ".cpp": Language.CPP,
            ".cc": Language.CPP,
            ".cxx": Language.CPP,
            ".c++": Language.CPP,
            ".go": Language.GO,
            ".java": Language.JAVA,
            ".kt": Language.KOTLIN,
            ".kts": Language.KOTLIN,
            ".js": Language.JS,
            ".mjs": Language.JS,
            ".ts": Language.TS,
            ".php": Language.PHP,
            ".proto": Language.PROTO,
            ".py": Language.PYTHON,
            ".pyw": Language.PYTHON,
            ".rst": Language.RST,
            ".rb": Language.RUBY,
            ".rs": Language.RUST,
            ".scala": Language.SCALA,
            ".swift": Language.SWIFT,
            ".md": Language.MARKDOWN,
            ".markdown": Language.MARKDOWN,
            ".tex": Language.LATEX,
            ".html": Language.HTML,
            ".htm": Language.HTML,
            ".sol": Language.SOL,
            ".cs": Language.CSHARP,
            ".cbl": Language.COBOL,
            ".cob": Language.COBOL,
            ".c": Language.C,
            ".h": Language.C,
            ".lua": Language.LUA,
            ".pl": Language.PERL,
            ".pm": Language.PERL,
            ".hs": Language.HASKELL,
            ".ex": Language.ELIXIR,
            ".exs": Language.ELIXIR,
            ".ps1": Language.POWERSHELL,
        }
        _, ext = os.path.splitext(path)
        return extension_to_language.get(ext.lower())

    def _chunk_corpus(
        self, corpus: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        """
        Chunk the corpus using language-specific splitters.

        Args:
            corpus: Dictionary of file_path -> {"title": title, "text": content}

        Returns:
            Dictionary of chunk_id -> {"title": title, "text": chunk_content}
        """
        new_corpus = {}

        for orig_id, doc in corpus.items():
            title = doc.get("title", "").strip()
            text = doc.get("text", "").strip()

            # Skip empty texts
            if not text:
                continue

            # Get language-specific splitter
            language = self._get_language_from_path(title)
            if language:
                try:
                    splitter = RecursiveCharacterTextSplitter.from_language(
                        language=language,
                        chunk_size=self.chunk_size,
                        chunk_overlap=self.chunk_overlap,
                    )
                except:
                    # Fallback to generic splitter
                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size=self.chunk_size,
                        chunk_overlap=self.chunk_overlap,
                    )
            else:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                )

            # Split only the text
            chunks = splitter.split_text(text)
            if not chunks:
                new_corpus[orig_id] = doc
                continue

            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{orig_id}_<chunk>_{i}"
                new_corpus[chunk_id] = {
                    "title": title,
                    "text": chunk_text,
                }

        return new_corpus

    def load_processed_data(
        self, preprocessed_dir: Path
    ) -> tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
        """
        Load processed corpus and chunks from disk.

        Args:
            preprocessed_dir: Path to preprocessed directory

        Returns:
            Tuple of (corpus, chunks)
        """
        corpus_file = preprocessed_dir / "corpus.json"
        chunks_file = preprocessed_dir / "chunks.json"

        with open(corpus_file, "r", encoding="utf-8") as f:
            corpus = json.load(f)

        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        return corpus, chunks
