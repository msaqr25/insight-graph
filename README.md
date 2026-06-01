# Insight Graph & RAG System for ML Research Papers

A **Retrieval-Augmented Generation** system that ingests academic ML papers, builds a vector search index and a Neo4j knowledge graph, and answers questions using LLM-powered retrieval and reasoning.

## Features

- **PDF Ingestion** — Upload academic papers; text is extracted, chunked, and embedded automatically via a Redis-backed async worker (ARQ).
- **Vector Search** — Chunks are embedded with `all-MiniLM-L6-v2` and stored in PostgreSQL/pgvector for cosine similarity retrieval.
- **Cross-Encoder Re-Ranking** — Top-20 vector results are re-ranked with `ms-marco-MiniLM-L-6-v2` for precision.
- **Knowledge Graph** — Entities (Concepts, Methods, Models, Papers, etc.) and their relations (PROPOSES, USES, CITES, etc.) are extracted from chunks using Google Gemini and stored in Neo4j.
- **RAG Query API** — Ask questions in natural language; the system retrieves relevant context and generates an answer via Gemini.
- **Evaluation Framework** — 20 curated questions across 4 categories (single-paper, cross-paper comparison, multi-hop, contradiction) scored with RAGAS metrics.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI |
| Vector DB | PostgreSQL + pgvector |
| Graph DB | Neo4j |
| Task Queue | ARQ + Redis |
| Embeddings | sentence-transformers |
| Re-ranker | cross-encoder |
| LLM | Google Gemini |
| Eval |RAGAS|
| ORM | SQLAlchemy 2.0 + asyncpg |
| PDF parsing | PyMuPDF |

## Getting Started

### Prerequisites

- Python 3.14+
- Docker & Docker Compose
- `uv` package manager

### Setup

```bash
# Install dependencies
uv sync --group dev

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
#   GOOGLE_API_KEY, OPENROUTER_API_KEY, NEO4J_PASSWORD, POSTGRES_PASSWORD
```

### Start Infrastructure

```bash
docker compose up -d
```

This starts PostgreSQL/pgvector (5432), Redis (6379), and Neo4j (7474/7687).

### Run the API + Worker

```bash
# Terminal 1 — API server
uv run fastapi dev api/main.py

# Terminal 2 — Background worker
uv run arq api.worker.worker.WorkerSettings
```

API docs are available at `http://localhost:8000/docs`.

### Ingest Papers

```bash
# Download sample ML papers from arXiv
./get_papers.sh

# Upload them via the API
uv run python ingest_papers.py

# Monitor processing status
uv run python poll_status.py
```

### Query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the key contribution of the Attention Is All You Need paper?"}'
```

## Evaluation

The system includes a 20-question benchmark across 4 categories:

| Category | Description |
|----------|-------------|
| Single-paper factual | Questions answerable from one paper |
| Cross-paper comparison | Compare findings across papers |
| Multi-hop relational | Multi-step reasoning across documents |
| Contradiction | Identify disagreements between papers |

```bash
uv run python api/eval/run_eval.py
```

## Testing

```bash
uv run pytest -v
```

## Papers Included

19 landmark ML papers are bundled in `papers/`:

Attention Is All You Need, BERT, Chain-of-Thought, Chinchilla, CLIP, Constitutional AI, DPR, FlashAttention, GAT, GPT-3, InstructGPT, LoRA, Mixtral, MMLU, Prompt Tuning, RAG, ReAct, Scaling Laws, ViT.

