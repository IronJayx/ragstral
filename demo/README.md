# Ragstral - RAG-powered Chat Interface

A SvelteKit application that demo a RAG (Retrieval-Augmented Generation) on the codebase indexed in /indexer.

The logic for the RAG is contained in `/src/lib/utils/ragstral.ts` and the endpoint it calls: `/src/routes/api/chain-of-thought/+server.ts` and `/src/routes/api/rag/+server.ts`.

## Features

- **Chain of Thought Gate**: Uses LLM to identify if clarification is needed before proceeding (ragstral only)
- **RAG Integration**: Searches relevant documents using vector embeddings and provides contextual responses (ragstral only)

## Architecture

The application supports three different endpoints:

### 1. Ragstral (Chain of Thought + RAG)

- **Chain of Thought Gate** (`/api/chain-of-thought`): Analyzes user queries to identify missing information
- **RAG Endpoint** (`/api/rag`): Generates embeddings using Mistral's `codestral-embed` model and searches Pinecone

### 2. GPT-4 Simple (`/api/gpt_simple`)

- Direct chat with OpenAI's GPT-4 model without RAG retrieval

### 3. Mistral Simple (`/api/mistral_simple`)

- Direct chat with Mistral's medium model without RAG retrieval

## Setup

### Prerequisites

- Node.js 18+
- Mistral AI API key
- OpenAI API key (for GPT-4 endpoint)
- Pinecone API key and configured index (for ragstral endpoint)

### Environment Variables

Create a `.env` file in the root directory:

```bash
MISTRAL_API_KEY=your_mistral_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
```

### Installation

```bash
# Install dependencies
pnpm install

# Run development server
pnpm run dev
```
