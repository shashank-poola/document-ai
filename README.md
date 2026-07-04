# Document Intelligence Platform

Enterprise-grade document extraction engine. Ingests PDF, image, and DOCX files, processes them asynchronously via Redis-backed workers, and produces structured JSON and Markdown output.

## Architecture

```
Upload API  →  Redis Queue  →  Worker Pool  →  Pipeline
                                                  ├── Preprocessing
                                                  ├── OCR (PaddleOCR)
                                                  ├── Boundary Detection
                                                  ├── Classification
                                                  ├── Extraction
                                                  ├── Validation
                                                  └── Output (JSON + Markdown)
```

**Queue:** [ARQ](https://github.com/python-arq/arq) on Redis — Python-native equivalent of BullMQ's worker pattern (Redis-backed jobs, retries, timeouts, horizontal scaling).

## Development Phases

| Phase | Scope | Status |
|-------|-------|--------|
| **0** | Foundation — schemas, config, storage, queue | Done |
| **1** | Vertical slice — single-page PDF/image through full pipeline | Done |
| **2** | Multi-page PDFs as one logical document (passthrough boundary) | Done |
| **3** | Multi-document boundary detection inside one file | Planned |
| **4** | Horizontal scaling hardening, observability | Planned |
| **5** | DOCX polish, embeddings, vector search | Planned |

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) or pip
- Docker (for Redis)
- PaddleOCR downloads models on first run

## Quick Start

### 1. Start Redis

```bash
docker compose up -d
```

### 2. Install dependencies

```bash
uv sync
# or: pip install -e ".[dev]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

### 4. Start the API

```bash
uv run docintel-api
# or: uvicorn app.main:app --reload
```

### 5. Start the worker (separate terminal)

```bash
uv run docintel-worker
# or: arq app.workers.settings.WorkerSettings
```

### 6. Upload a document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@invoice.pdf"
```

Poll status:

```bash
curl "http://localhost:8000/api/v1/documents/{job_id}/status"
```

Fetch results:

```bash
curl "http://localhost:8000/api/v1/documents/{job_id}/result"
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/documents/upload` | Upload and enqueue document |
| `GET` | `/api/v1/documents/{job_id}/status` | Job status |
| `GET` | `/api/v1/documents/{job_id}/result` | Structured extraction output |

## Project Structure

```
app/
├── ingestion/          # Upload API
├── queue/              # Redis job enqueue client
├── workers/            # Background worker (ARQ)
├── pipeline/           # Stage orchestration
├── preprocessing/      # PDF, image, DOCX normalization
├── ocr/                # PaddleOCR provider
├── boundary_detection/ # Document boundary logic
├── classification/     # Document type classification
├── extraction/         # Structured field extraction
├── validation/         # Field and cross-field validation
├── output/             # JSON and Markdown generation
├── storage/            # Pluggable storage backend
├── schemas/            # Pydantic contracts
└── config/             # Settings
```

## Supported Inputs (MVP)

- PDF (digital and scanned)
- Images: PNG, JPG, JPEG, TIFF, WEBP
- DOCX

## Supported Document Types (MVP)

- Invoice
- Receipt
- Purchase Order

## Running Tests

```bash
uv run pytest
```

## Scaling

Run multiple worker processes against the same Redis instance:

```bash
# Terminal 1
uv run docintel-worker

# Terminal 2
uv run docintel-worker
```

Each worker independently picks jobs from the queue.
