# Document Intelligence Platform

An asynchronous document extraction engine that ingests business documents (PDF, images, DOCX), processes them through a staged pipeline, and returns structured **JSON** and human-readable **Markdown**.

This repository is the **backend extraction engine** — not a full enterprise product. It demonstrates the core architecture: queue-driven ingestion, modular pipeline stages, provider-swappable OCR, and structured output with validation.

---

## Problem This Solves

Enterprises receive thousands of documents in varying formats. A single PDF may contain multiple logical documents (e.g. two invoices and a receipt). The platform is designed to:

1. Accept documents without blocking the upload request
2. Normalize and read each file (OCR when needed)
3. Detect where one document ends and another begins
4. Classify document type (invoice, receipt, purchase order)
5. Extract structured fields (vendor, totals, dates, etc.)
6. Validate extracted data and flag low-confidence results for review
7. Store JSON + Markdown for downstream systems

---

## Current Status (Phases 0–2 Complete)

| Phase | Scope | Status |
|-------|-------|--------|
| **0** | Schemas, config, storage, queue contracts | Done |
| **1** | End-to-end vertical slice (upload → output) | Done |
| **2** | Multi-page PDFs, async workers, web UI | Done |
| **3** | Multi-document boundary detection in one file | Planned |
| **4** | Observability, retries, production hardening | Planned |
| **5** | Embeddings, vector search, cloud connectors | Planned |

**What works today:** async upload, Redis-backed workers, full pipeline execution, PaddleOCR, heuristic classification/extraction, validation, JSON/Markdown output, batch web UI.

**What is not production-ready yet:** boundary detection (passthrough only), extraction accuracy across all invoice templates, embeddings, PostgreSQL/S3/Qdrant, enterprise connectors (SharePoint, S3, email).

---

## High-Level Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│  Web UI     │     │  Upload API │────▶│  Redis Queue │────▶│  Worker Pool (stateless)    │
│  (React)    │────▶│  (FastAPI)  │     │  (ARQ)       │     │                             │
└─────────────┘     └─────────────┘     └──────────────┘     └──────────────┬──────────────┘
                                                                              │
                                                                              ▼
                                                            ┌─────────────────────────────┐
                                                            │  Pipeline (sequential)      │
                                                            │  1. Preprocessing           │
                                                            │  2. OCR (PaddleOCR)         │
                                                            │  3. Boundary Detection      │
                                                            │  4. Classification          │
                                                            │  5. Extraction              │
                                                            │  6. Validation              │
                                                            │  7. Output (JSON + MD)      │
                                                            └──────────────┬──────────────┘
                                                                           │
                                                                           ▼
                                                            ┌─────────────────────────────┐
                                                            │  Local Storage (./data)     │
                                                            │  jobs/{id}/original|ocr|output │
                                                            └─────────────────────────────┘
```

### Why async?

Uploads are never processed synchronously. The API stores the file, enqueues a job, and returns immediately. Workers pull jobs from Redis independently — this allows horizontal scaling (run N workers on N machines against one Redis instance).

### Queue technology

**[ARQ](https://github.com/python-arq/arq)** on Redis — Python-native job queue with retries, timeouts, and worker pools. Same operational pattern as BullMQ (Redis-backed, worker pulls jobs), implemented for the Python stack.

---

## Pipeline Stages (What Happens to Each Document)

Each uploaded file becomes a **job**. A worker runs the pipeline sequentially:

| Stage | Module | What it does |
|-------|--------|--------------|
| **Preprocessing** | `app/preprocessing/` | Split PDF into pages, normalize images, extract DOCX text/images. Tags each page as native text or needs-OCR. |
| **OCR** | `app/ocr/` | PaddleOCR extracts text, layout blocks, confidence. Digital PDFs with embedded text can skip full OCR. |
| **Boundary detection** | `app/boundary_detection/` | Groups pages into logical documents. *Currently passthrough (all pages = one segment).* Phase 3 adds real splitting. |
| **Classification** | `app/classification/` | Identifies document type: invoice, receipt, or purchase order (keyword heuristics). |
| **Extraction** | `app/extraction/` | Pulls structured fields per document type. Invoice uses multi-strategy layout parser (`invoice_layout.py`). |
| **Validation** | `app/validation/` | Field-level checks (dates, currency, required fields) and cross-field rules (subtotal + tax ≈ total). |
| **Output** | `app/output/` | Writes `structured.json` and `summary.md` per segment under `data/jobs/{job_id}/output/`. |

### Job lifecycle

```
PENDING → QUEUED → PREPROCESSING → OCR → BOUNDARY_DETECTION → CLASSIFICATION
         → EXTRACTION → VALIDATION → OUTPUT → COMPLETED
                                              ↘ FAILED
                                              ↘ NEEDS_REVIEW (low confidence)
```

### Data contracts

Every stage reads and writes **Pydantic schemas** in `app/schemas/`. Stages do not import each other — they communicate through typed artifacts (`Page`, `OCRPageResult`, `DocumentSegment`, `ExtractionResult`, etc.). This keeps stages testable and swappable.

---

## Repository Layout

```
pdf-parser/
├── app/
│   ├── ingestion/           # FastAPI upload, status, result endpoints
│   ├── queue/               # Redis job enqueue client
│   ├── workers/             # ARQ worker — picks jobs and runs pipeline
│   ├── pipeline/            # Orchestrates stage execution
│   ├── preprocessing/       # PDF, image, DOCX normalization
│   ├── ocr/                 # PaddleOCR provider (interface + implementation)
│   ├── boundary_detection/  # Page grouping (passthrough in Phase 2)
│   ├── classification/      # Document type identification
│   ├── extraction/          # Structured field extraction per type
│   ├── validation/          # Rules + confidence scoring
│   ├── output/              # JSON and Markdown generation
│   ├── storage/             # Filesystem backend (S3-ready interface)
│   ├── schemas/             # Pydantic models — pipeline contracts
│   ├── config/              # Environment-driven settings
│   └── utils/               # Logging, exceptions
├── web/                     # React upload UI (drag & drop, live status)
├── data/
│   ├── jobs/                # Per-job artifacts (gitignored)
│   └── samples/             # Test documents
├── tests/
├── docker-compose.yml       # Redis
├── pyproject.toml
└── .env.example
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Docker (for Redis)
- Bun or npm (for web UI, optional)

PaddleOCR downloads models on first worker run (~2–5 minutes once, then cached).

### 1. Clone and configure

```bash
cp .env.example .env
```

### 2. Start Redis

```bash
docker compose up -d
```

### 3. Install Python dependencies

```bash
uv sync --extra dev
```

### 4. Start the API (terminal 1)

```bash
uv run docintel-api
```

API: http://localhost:5000 — docs at http://localhost:5000/docs

### 5. Start the worker (terminal 2)

```bash
uv run docintel-worker
```

The worker must be running for documents to process. Without it, jobs stay in `queued`.

### 6. Start the web UI (terminal 3, optional)

```bash
cd web
bun install && bun dev
```

UI: http://localhost:5173 — drag & drop PDFs, images, or DOCX. Supports batch upload with live status and JSON/Markdown preview.

### 7. Or upload via cURL

```bash
curl -X POST "http://localhost:5000/api/v1/documents/upload" \
  -F "file=@invoice.pdf"
```

Poll status: `GET /api/v1/documents/{job_id}/status`  
Get results: `GET /api/v1/documents/{job_id}/result`

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/api/v1/documents/upload` | Upload file, enqueue job (returns `202`) |
| `GET` | `/api/v1/documents/{job_id}/status` | Job status and progress |
| `GET` | `/api/v1/documents/{job_id}/result` | Structured extraction output |

### Supported file types

| Format | Extensions |
|--------|------------|
| PDF | `.pdf` |
| Images | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.webp` |
| Word | `.docx` |

### Supported document types (MVP)

- Invoice
- Receipt
- Purchase Order

---

## Configuration

Copy `.env.example` to `.env`:

```env
# Application
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=5000

# Storage
STORAGE_ROOT=./data
MAX_UPLOAD_SIZE_MB=50

# Redis / Queue
REDIS_URL=redis://localhost:6379/0
QUEUE_NAME=document-processing
JOB_TIMEOUT_SECONDS=600
JOB_MAX_RETRIES=3

# OCR (PaddleOCR)
OCR_LANG=en
OCR_USE_GPU=false
OCR_DPI=200
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

# Validation
REVIEW_CONFIDENCE_THRESHOLD=0.75
```

| Variable | Purpose |
|----------|---------|
| `REDIS_URL` | Redis connection for job queue |
| `STORAGE_ROOT` | Where job artifacts are stored |
| `OCR_USE_GPU` | Enable GPU for PaddleOCR (requires CUDA) |
| `REVIEW_CONFIDENCE_THRESHOLD` | Below this, job status becomes `needs_review` |
| `JOB_TIMEOUT_SECONDS` | Max seconds per job (set on worker, not per enqueue) |

---

## Scaling

Run multiple workers against the same Redis:

```bash
# Machine 1
uv run docintel-worker

# Machine 2
uv run docintel-worker
```

Each worker independently pulls jobs. Workers are stateless — scale by adding processes.

### Rough throughput (500 PDFs, CPU, ~1–2 pages each)

| Workers | Time to first result | Time for all 500 |
|---------|---------------------|------------------|
| 1 | ~30–90 sec | ~4–8 hours |
| 4 | ~30–90 sec | ~1–2 hours |
| 8 + GPU | ~15–30 sec | ~30–60 min |

Results stream incrementally — the first JSON/Markdown appears within about a minute, not after the entire batch finishes.

---

## Design Principles

1. **Modular pipeline** — Each stage is isolated with a clear input/output contract.
2. **Queue-driven** — Upload never blocks on processing.
3. **Provider-independent OCR** — `OCRProvider` interface; PaddleOCR is the default implementation.
4. **Schema-first** — Pydantic models in `app/schemas/` define the pipeline artifact chain.
5. **Extensible document types** — Classifier and extractor registries per `DocumentType`.
6. **Honest confidence** — Validation scores fields; low confidence triggers `needs_review`.

---

## Known Limitations (Phase 2)

These are intentional gaps documented for the next phases:

| Limitation | Impact | Planned fix |
|------------|--------|-------------|
| Passthrough boundary detection | Multi-document PDFs treated as one segment | Phase 3: layout + heuristic boundary splitter |
| Heuristic extraction | Breaks on unfamiliar invoice templates | Phase 3+: OCR bounding-box regions or LLM structured extraction |
| Local filesystem storage | Not suitable for multi-node production | Phase 4: S3-compatible object storage |
| No embeddings | No semantic search | Phase 5: vector generation + Qdrant |
| No enterprise connectors | Manual upload only | Phase 5: S3, SharePoint, email ingestion |

---

## Testing

```bash
uv run pytest
uv run ruff check app tests
```

Unit tests cover classification, extraction (WordPress + TCPDF invoice samples), validation, and preprocessing.

---

## Roadmap

- **Phase 3** — Multi-document boundary detection; layout-aware extraction using OCR bounding boxes
- **Phase 4** — Prometheus metrics, dead-letter queue, idempotency hardening, S3 storage
- **Phase 5** — Embeddings, Qdrant, PostgreSQL job metadata, cloud connectors
- **Phase 6** — Human review UI, batch dashboard, continuous learning from corrections

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Uvicorn |
| Queue | ARQ + Redis |
| OCR | PaddleOCR 3.x |
| PDF | PyMuPDF |
| Schemas | Pydantic v2 |
| Logging | structlog |
| Web UI | React, Vite |
| Tooling | uv, pytest, ruff |

---

## License

Private / internal — adjust as needed.

<!-- retrigger webhook -->
