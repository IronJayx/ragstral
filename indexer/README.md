# RAG Indexing Pipeline for GitHub Repositories

A simplified pipeline for fetching GitHub repositories (via ZIP downloads), processing code, computing embeddings, and indexing them in Pinecone for semantic code search.

Note: this module is making extensive usage of the code from Mistral cookbook for chunking and computing code embeddings with codestral-embed: https://colab.research.google.com/github/mistralai/cookbook/blob/main/mistral/embeddings/code_embedding.ipynb#scrollTo=al-RhKoCsXfF

## Indexing Pipeline

- **ZIP Download**: Download github repository .zip archive given repo url and version.
- **Code Processing**: Extract and chunk code files using language-aware splitters
- **Mistral Embeddings**: Generate embeddings using Mistral's `codestral-embed` model
- **Pinecone Indexing**: Index chunks in Pinecone using computed embeddings and metadata.

## Quick Start

1. **Install dependencies**:

   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install .
   ```

2. **Set up environment variables**:

   ```bash
   # Create .env file with your API keys
   echo "MISTRAL_API_KEY=your_key_here" > .env
   echo "PINECONE_API_KEY=your_key_here" >> .env
   ```

3. **Run the pipeline**:
   ```bash
   .venv/bin/python pipeline.py https://github.com/modal-labs/modal-client v1.0.3
   ```

## Reproduction

### Run Example Script

```bash
chmod +x example.sh
./example.sh
```
