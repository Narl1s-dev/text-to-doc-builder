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

The response contains `download_url` when the `.docx` file is ready.
