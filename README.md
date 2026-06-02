# Text To Doc Builder

Backend API for creating document artifacts from natural-language requests.

## Current Stage

Stage 1 contains the FastAPI application skeleton:

- application factory;
- `/health` endpoint;
- environment-based settings;
- basic logging setup;
- package structure for later generation pipeline work.

Stage 2 adds the first document creation API:

- `POST /documents`;
- optional internal token auth through `X-API-Token` or `Authorization: Bearer <token>`;
- SQLite persistence for generation requests and artifacts;
- artifact creation with `processing` status.

Stage 3 adds the planning layer:

- `GenerationSpec` and `ArtifactPlan` schemas;
- default values for missing user parameters;
- OpenRouter client;
- prompt builder;
- LLM response validation;
- saved planning attempts in `llm_generations`.

If `OPENROUTER_API_KEY` or `OPENROUTER_MODEL` is not configured, local requests keep working with fallback defaults and warnings.

Stage 4 adds the first real artifact generation:

- renderer registry;
- `.docx` renderer based on `python-docx`;
- artifact files saved to `storage/artifacts`;
- `GET /documents/{document_id}`;
- `GET /documents/{document_id}/download`;
- artifact status updated to `ready` or `failed`.

Stage 5 stabilizes the end-to-end prototype:

- a minimal `prompt` request creates a ready `.docx`;
- `overrides.title` is reflected in the generated file;
- OpenRouter planning failures are converted into controlled pipeline failures;
- renderer failures are converted into controlled pipeline failures;
- the generation pipeline is tested independently from HTTP and external network calls.

Stage 6 prepares the format seam:

- canonical `ArtifactFormat` enum;
- explicit list of known future formats;
- validation that only renderable formats are accepted by the public API;
- renderer registry tests;
- future renderer notes in `docs/future-renderers.md`.

Stage 7 adds an internal test UI:

- `GET /ui`;
- prompt form;
- optional overrides JSON;
- optional API token field;
- status, warnings, errors, and download button.

Stage 8 adds a test deployment path:

- Dockerfile;
- docker-compose;
- server `.env` example;
- persistent `storage` volume;
- VDSina deployment guide in `docs/deploy-vdsina.md`.

Stage 9 switches generation to a job-based async backend:

- `POST /documents` creates a request, artifact, and job, then returns `202 Accepted`;
- generation runs in a worker that reuses the existing `GenerationPipeline`;
- `GET /documents/{document_id}` returns `queued`, `processing`, `ready`, or `failed`;
- responses include `job_id`, `current_stage`, `status_url`, and `download_url` when ready;
- `WORKER_CONCURRENCY` controls worker parallelism;
- processing jobs are requeued on worker startup.

Stage 10 adds the document specification contract:

- `DocumentSpec` / `document_spec.json` as the stable intermediate document contract;
- `content_markdown` for full document content;
- planning diagnostics now include `document_spec`;
- every planned job saves `{document_id}.document_spec.json` next to the generated artifact;
- the current `.docx` renderer can render from `DocumentSpec` while future codegen/sandbox work is prepared.

Stage 11 adds LLM codegen and a Docker sandbox for `.docx`:

- a codegen prompt asks an LLM for Python code;
- generated code must read `/input/document_spec.json` and write `/output/result.docx`;
- sandbox execution runs without network and with CPU/RAM/timeout limits;
- generated code, stdout, stderr, and sandbox result JSON are saved under `storage/artifacts/codegen/{document_id}`;
- if codegen or sandbox execution fails, the built-in `.docx` renderer is used as fallback.

Stage 12 adds `.docx` validation and repair retry:

- generated `.docx` files are opened with `python-docx`;
- validation checks readable text and required headings from `DocumentSpec`;
- failed sandbox or validation attempts can trigger a codegen repair prompt;
- repair receives `document_spec.json`, previous Python code, sandbox logs, and validation errors;
- each attempt saves generated code, stdout, stderr, sandbox result, and validation result diagnostics.

## Run Locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Create a document:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/documents `
  -ContentType 'application/json' `
  -Body '{"prompt":"Сделай краткий документ по итогам встречи"}'
```

The response is accepted immediately with `status_url`. Poll that URL until the status becomes `ready` or `failed`. A ready document contains `download_url`.

Run the standalone worker when `WORKER_ENABLED=false` for the API process:

```powershell
python -m app.worker
```

Build the application and `.docx` sandbox runtime images:

```powershell
docker compose build --no-cache
```

With Docker Compose:

```powershell
docker compose build --no-cache
docker compose up -d
```

Open the test UI:

```powershell
Start-Process http://localhost:8000/ui
```

## Test Deploy

See [docs/deploy-vdsina.md](docs/deploy-vdsina.md).
