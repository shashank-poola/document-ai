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

### 6. Start the web UI (optional, separate terminal)

```bash
cd web
bun install   # or npm install
bun dev       # opens http://localhost:5173
```

Drag & drop PDFs, images, or DOCX files. The UI uploads to the API, polls job status, and displays JSON / Markdown output.

## How Companies Upload Documents (Current Version)

| Method | How |
|--------|-----|
| **Web UI** | `http://localhost:5173` — drag & drop or browse (supports batch upload) |
| **REST API** | `POST /api/v1/documents/upload` with `multipart/form-data` |
| **cURL** | `curl -F "file=@invoice.pdf" http://localhost:8000/api/v1/documents/upload` |

There is no SharePoint/S3/email connector yet — those are Phase 5+ roadmap items.

## Environment Variables (`.env`)

Copy `.env.example` to `.env` in the project root:

```env
APP_NAME=document-intelligence
APP_ENV=development
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

STORAGE_ROOT=./data
MAX_UPLOAD_SIZE_MB=50

REDIS_URL=redis://localhost:6379/0
QUEUE_NAME=document-processing
JOB_TIMEOUT_SECONDS=600
JOB_MAX_RETRIES=3

OCR_LANG=en
OCR_USE_GPU=false
OCR_DPI=200
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

REVIEW_CONFIDENCE_THRESHOLD=0.75
```

For production, set `APP_ENV=production`, point `REDIS_URL` to your managed Redis, and increase worker count.

## Processing Time Estimates (500 PDFs)

Rough estimates with the **current** stack (PaddleOCR on CPU, 1–2 pages per PDF):

| Setup | Time to first result | Time for all 500 |
|-------|---------------------|------------------|
| 1 worker, CPU | ~30–90 sec | ~4–8 hours |
| 4 workers, CPU | ~30–90 sec | ~1–2 hours |
| 8 workers + GPU | ~15–30 sec | ~30–60 min |

Assumptions: average 1–2 page scanned/digital PDF, ~30–60 sec OCR per page on CPU. Digital PDFs with extractable text are faster (native text path skips full OCR).

**What the company sees:**
- First completed JSON/Markdown within **~1 minute** of worker picking up the first job
- Results appear incrementally as each document finishes (not all at once)
- Web UI shows live queue status per file

To process 500 PDFs faster: run multiple workers (`uv run docintel-worker` in N terminals) and/or enable `OCR_USE_GPU=true` with a CUDA GPU.

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
