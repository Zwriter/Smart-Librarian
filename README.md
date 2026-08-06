# Smart Librarian AI-RAG

Smart Librarian is a full-stack book recommendation application. A user describes what they want to read in the React interface, and the FastAPI backend combines input filtering, semantic retrieval from a Chroma catalogue, and an OpenAI recommendation workflow to return one book, its rationale, and the complete locally stored summary.

The browser never receives provider credentials. It communicates with the backend over the documented REST API, while the backend owns model access, catalogue ingestion, retrieval, tool execution, request tracing, structured logging, and usage aggregation.

## Features

- Natural-language book recommendations based on the local catalogue.
- Semantic book retrieval using Chroma and OpenAI embeddings.
- Input validation, configurable content filtering, and bounded conversation history.
- Complete local book summaries returned with each recommendation.
- React chat interface with retry, loading, error, and clear-conversation states.
- Correlation IDs on every API response for request tracing.
- Privacy-aware structured logs that exclude prompts, completions, summaries, and secrets.
- Aggregate token and estimated-cost reporting when model pricing is configured.
- Local development and Docker Compose workflows.

## Architecture

```text
Browser
	|
	| POST /chat
	v
React + TypeScript + Vite (development) / Nginx (Docker)
	|
	| CORS-enabled HTTP API
	v
FastAPI backend
	|
	+--> Input filter and domain validation
	+--> Chroma vector store <--> OpenAI embeddings
	+--> Retriever and recommendation prompt <--> OpenAI chat model
	+--> Tool call executor and local book repository
	+--> Correlation-aware structured logging and usage aggregation
```

The normal request path is:

1. The frontend trims and submits a question with up to 19 previous messages.
2. FastAPI validates the request and enforces body and history limits.
3. The input filter rejects unsupported or unsafe content.
4. The retriever searches the ingested Chroma catalogue for relevant books.
5. The recommendation service asks the configured chat model to select a book.
6. The summary tool resolves the complete summary from the local catalogue.
7. The API returns the recommendation and summary, together with `X-Correlation-ID`.

## Repository Layout

```text
backend/
	app/
		api/          FastAPI routes and dependencies
		core/         Configuration, correlation, exceptions, and logging
		domain/       Request, response, book, and recommendation models
		services/     Retrieval, LLM, ingestion, filtering, tools, and storage
		scripts/      Catalogue ingestion entry points
	data/           Book summaries and filter configuration
	docs/           API, operations, and privacy documentation
	tests/          Backend unit and API tests
frontend/
	src/
		components/   Conversation, composer, recommendation, and error UI
		hooks/        Chat state and API orchestration
		services/     Browser API client and tests
		styles/       Application stylesheets
	public/         Static frontend assets
	tests/          Frontend component and integration tests
docker-compose.yml
.env.example
```

## Requirements

For local development:

- Python 3.11 or newer
- Node.js 20.19+ or 22.12+
- npm 10+
- An OpenAI API key for chat and catalogue ingestion

For the container workflow:

- Docker
- Docker Compose

## Quick Start: Local Development

### 1. Configure the backend

From the repository root, copy the environment template and set a real key:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`. Keep this file untracked. The backend loads configuration from the repository root or `backend/.env`.

### 2. Install and start the backend

```powershell
Set-Location backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`. OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

Check liveness from another terminal:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### 3. Ingest the catalogue

Before the first recommendation, populate Chroma with the local catalogue:

```powershell
Set-Location backend
\.venv\Scripts\Activate.ps1
python -m app.scripts.ingest_books
```

Ingestion validates `backend/data/book_summaries.json`, creates embeddings, and upserts stable document IDs. It is repeatable and requires a configured OpenAI key plus a writable Chroma directory.

### 4. Install and start the frontend

In a new terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`. The frontend defaults to `http://127.0.0.1:8000` as its backend origin. If the backend uses another address, set `VITE_API_BASE_URL` before starting Vite or place it in `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8001
```

This value must be an absolute backend origin without `/chat` and without a trailing slash. `VITE_` variables are exposed to browser code, so never put secrets in them.

## Docker Compose

The Compose stack builds both services, waits for the backend health check, and persists Chroma data and backend logs in named volumes.

From the repository root:

```powershell
Copy-Item .env.example .env
# Set OPENAI_API_KEY in .env before starting the stack.
docker compose up --build
```

Use the application at `http://localhost:8080/` and the API at `http://localhost:8000/`. The frontend image is served by Nginx and is built with `VITE_API_BASE_URL=http://localhost:8000`.

Stop the stack while retaining named volumes:

```powershell
docker compose down
```

Remove the local Chroma index and logs only when intentionally resetting persisted data:

```powershell
docker compose down -v
```

To build the frontend against a different browser-visible backend origin, rebuild it with the corresponding argument:

```powershell
docker compose build --build-arg VITE_API_BASE_URL=http://localhost:8001 frontend
docker compose up
```

The API URL is embedded in the static frontend bundle at build time.

## Configuration

The complete starting point is `.env.example`. The principal settings are:

| Setting | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Provider credential for chat and ingestion | Required |
| `OPENAI_CHAT_MODEL` | Chat completion model | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `CHROMA_PERSIST_DIRECTORY` | Persistent vector-store directory | `backend/.chroma` |
| `CHROMA_COLLECTION_NAME` | Chroma collection name | `books` |
| `BOOK_DATA_PATH` | Book catalogue JSON path | `backend/data/book_summaries.json` |
| `FILTER_CONFIG_PATH` | Filter configuration JSON path | `backend/data/filter_config.json` |
| `CORS_ALLOWED_ORIGINS` | Explicit browser origins allowed by the API | Local frontend origins |
| `TOP_K_RESULTS` | Number of retrieved books | `5` |
| `MAX_QUESTION_LENGTH` | Backend question limit | `500` |
| `MAX_HISTORY_MESSAGES` | Conversation history limit | `20` |
| `MAX_REQUEST_BODY_BYTES` | Maximum HTTP request body | `100000` |
| `LOG_FILE_PATH` | Rotating JSON log path | `backend/logs/app.log` |
| `LOG_PRIVACY_MODE` | Logging privacy mode | `redact` |
| `MODEL_PRICING` | USD pricing per 1,000,000 tokens | Empty unless configured |

Keep `CORS_ALLOWED_ORIGINS` explicit in production. Wildcard `*` is rejected. Chroma anonymized telemetry is disabled by the application and Compose runtime.

## API Overview

Base URL: `http://127.0.0.1:8000`

All responses include `X-Correlation-ID`. A valid caller-supplied UUID is preserved; otherwise the backend generates one.

### `GET /health`

Liveness check. It does not require an OpenAI key or an initialized Chroma collection.

```json
{"status":"ok"}
```

### `GET /ready`

Readiness check for the API key, book data, filter configuration, and Chroma initialization. It returns `200` with `{"status":"ready"}` when ready and `503` with a generic error when not ready.

### `POST /chat`

Request:

```json
{
	"question": "I want a science-fiction book about politics",
	"history": [
		{"role": "user", "content": "I enjoyed complex world-building."}
	]
}
```

The question is required, trimmed, and limited to 500 characters by default. History defaults to an empty array and is limited to 20 validated messages. Unknown fields are rejected.

Success response:

```json
{
	"recommendation": {
		"title": "Dune",
		"author": "Frank Herbert",
		"rationale": "It matches the request."
	},
	"summary": "Complete local book summary."
}
```

Common errors are `400` for rejected input, `404` for a missing local book, `413` for an oversized request body, `422` for FastAPI validation errors, and `502` for provider, retrieval, tool, catalogue, or filter-configuration failures. Internal exception details, prompts, completions, tool arguments, secrets, and filesystem paths are not returned.

See [backend/docs/api.md](backend/docs/api.md) for the complete contract and CORS details.

## Frontend Behavior

- Messages and the current recommendation remain in React memory for the active browser tab.
- Refreshing, closing the tab, or opening a new tab starts a new conversation.
- The visible conversation is capped at 20 messages.
- The composer is disabled during a request and duplicate submissions are ignored.
- A failed request preserves the question and history for **Retry request**.
- **Clear shelf** removes messages, errors, and the current recommendation immediately.
- The frontend trims and limits questions to 2,000 characters before submission; the backend remains the authoritative validator.

## Validation and Tests

Run the backend checks from `backend`:

```powershell
python -m pytest tests
python -m ruff check .
python -m mypy app
```

Run the frontend checks from `frontend`:

```powershell
npm run build
npm run lint
npm test
```

The frontend tests use Vitest, React Testing Library, jsdom, and MSW. They mock API calls and do not require a running backend. Focused provider-free backend observability tests are available with:

```powershell
python -m pytest tests/core/test_observability.py tests/core/test_logging_config.py
```

## Security and Privacy

`OPENAI_API_KEY` is loaded at runtime and is not copied into images, committed to Git, written to logs, or returned in API responses. Do not place it in a Dockerfile, Compose `environment` value, frontend variable, source file, or build output.

Logs contain operational metadata such as timestamps, event names, correlation IDs, paths, status codes, duration, model names, token counts, and estimated-cost status. By default they exclude questions, conversation history, prompts, completions, summaries, tool arguments, and raw provider payloads. Treat local logs as diagnostic artifacts, restrict access, and apply deployment-specific retention.

If a provider key is exposed, revoke it and create a replacement immediately. Read [backend/docs/privacy.md](backend/docs/privacy.md) for the full logging and retention policy.

## Operations and Troubleshooting

Use this sequence when diagnosing a request:

1. Check `/health` to confirm the process is alive.
2. Check `/ready` to identify configuration, data, or Chroma readiness failures.
3. Capture `X-Correlation-ID` from the response.
4. Search structured logs for the matching `correlation_id`.
5. Inspect aggregate token and cost fields without expecting prompt or completion content.

For Windows, use `python -m uvicorn` rather than a copied `uvicorn.exe` launcher if the virtual environment has moved. If port `8000` is busy, stop the existing process or start Uvicorn on another port and update `VITE_API_BASE_URL`.

After backend source changes, rebuild the Compose image because the service copies application source into the image rather than bind-mounting `backend/app`:

```powershell
docker compose build backend
docker compose up -d backend
docker compose exec backend python -m app.scripts.ingest_books
```

See [backend/docs/operations.md](backend/docs/operations.md) for observability and storage guidance.

## Further Documentation

- [Backend development and deployment guide](backend/README.md)
- [Frontend development and deployment guide](frontend/README.md)
- [REST API contract](backend/docs/api.md)
- [Operations and observability](backend/docs/operations.md)
- [Privacy rules](backend/docs/privacy.md)
