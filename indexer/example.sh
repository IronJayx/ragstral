#!/bin/bash
# Example script for running the RAG indexing pipeline

set -e  # Exit on any error

echo "RAG Indexing Pipeline Example"
echo "============================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: Please create a .env file with your API keys"
    echo "Copy .env.example to .env and fill in your MISTRAL_API_KEY and PINECONE_API_KEY"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run: uv venv && source .venv/bin/activate && uv pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Example: Index modal-labs/modal-client with specific tags
REPO_URL="https://github.com/modal-labs/modal-client"
TAGS="v0.58.94 v1.0.3 v0.77.0"

# REPO_URL="https://github.com/IronJayx/ragstral"
# TAGS=""

echo "Indexing repository: $REPO_URL"
echo "Tags: $TAGS"
echo ""

# Run the pipeline
.venv/bin/python pipeline.py $REPO_URL $TAGS

echo ""
echo "Pipeline completed successfully!"
echo "You can now search for code using the indexed repositories." 