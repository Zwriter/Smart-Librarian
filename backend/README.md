# Smart Librarian Backend

FastAPI backend for semantic book recommendations. The service owns book ingestion, filtering, retrieval, OpenAI integration, tool execution, request correlation, structured logging, and usage aggregation. The React frontend communicates with it only through the documented REST API.

## Requirements

- Python 3.11 or newer
- An OpenAI API key for `/chat` and ingestion
- Docker and Docker Compose for the container workflow

## Quick Start

From the repository root, create `.env` from the provided template and set a real `OPENAI_API_KEY`:

```powershell
Copy-Item .env.example .env
```

Then open a terminal in `backend` and create the backend virtual environment:

```powershell
Set-Location backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the API with the module form of Uvicorn:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Using `python -m uvicorn` ensures that Uvicorn runs from the active backend environment. On Windows, a copied or moved virtual environment can leave a stale `uvicorn.exe` launcher pointing to an old path. The module command avoids that launcher problem.

The interactive OpenAPI document is available at `http://127.0.0.1:8000/docs` while the service is running. Check that the process is alive with:

```powershell
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
```

Expected response:

```json
{"status":"ok"}
```

Before calling `/chat` for the first time, populate the Chroma catalogue with the ingestion command in [Catalogue Ingestion](#catalogue-ingestion). An initialized but empty Chroma collection makes the API ready while retrieval still has no books to search.

If port `8000` is already in use, stop the existing process or start another instance on a different port:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

## Configuration

The application loads `.env` from the repository root or from `backend/.env`. The most important settings are:

| Setting | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Provider credential required for chat and ingestion | Required |
| `OPENAI_CHAT_MODEL` | Chat completion model | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `CHROMA_PERSIST_DIRECTORY` | Persistent vector-store directory | `backend/.chroma` locally |
| `BOOK_DATA_PATH` | Book catalogue JSON file | `backend/data/book_summaries.json` locally |
| `FILTER_CONFIG_PATH` | Input-filter JSON file | `backend/data/filter_config.json` locally |
| `CORS_ALLOWED_ORIGINS` | Explicit frontend origins | Local Vite and React origins |
| `TOP_K_RESULTS` | Number of retrieved books | `5` |
| `MAX_QUESTION_LENGTH` | Input-filter question limit | `500` |
| `MAX_HISTORY_MESSAGES` | Conversation history limit | `20` |
| `MAX_REQUEST_BODY_BYTES` | HTTP request body limit | `100000` |
| `LOG_FILE_PATH` | Structured JSON log path | `backend/logs/app.log` locally |
| `LOG_MAX_BYTES` | Maximum size of one log file | `10000000` |
| `LOG_BACKUP_COUNT` | Number of rotated log files | `5` |
| `LOG_PRIVACY_MODE` | Logging privacy behavior | `redact` |
| `MODEL_PRICING` | JSON pricing in USD per 1,000,000 tokens | Empty unless configured |

Chroma anonymized telemetry is disabled in the application and Compose runtime with `ANONYMIZED_TELEMETRY=false`.

Keep `CORS_ALLOWED_ORIGINS` explicit in production. Wildcard `*` is rejected by settings validation.

## API Key Security

`OPENAI_API_KEY` is loaded at runtime from environment configuration. It is not copied into the Docker image, committed to Git, written to application logs, returned in API responses, or included in the Docker build context. The backend `.dockerignore` excludes `.env`, secret files, keys, certificates, virtual environments, logs, and local Chroma data.

For local Docker Compose, keep the key in the untracked root `.env` file. For production, inject it through the deployment platform's secret manager or runtime environment rather than placing it in a Dockerfile, Compose `environment` value, source file, or image layer. Do not run `docker compose config` in shared output because rendered configuration can include environment values.

If a key is ever committed, pasted into a ticket, or exposed in a build log, revoke it and create a replacement immediately.

## Validation

Run the complete backend gate from this directory:

```powershell
python -m pytest tests
python -m ruff check .
python -m mypy app
```

The focused observability checks are provider-free:

```powershell
python -m pytest tests/core/test_observability.py tests/core/test_logging_config.py
```

## Catalogue Ingestion

Ingestion validates `data/book_summaries.json`, embeds each book, and upserts stable document IDs into the configured Chroma collection. It is repeatable.

```powershell
python -m app.scripts.ingest_books
```

The command requires a configured OpenAI key and a writable Chroma directory. In Docker, use the persistent `/app/.chroma` volume.

## Docker Compose

From the repository root, configure `.env` and run:

```powershell
docker compose up --build
```

The API is exposed on port `8000`. Compose persists Chroma data in `chroma-data` and structured logs in `backend-logs`. The service health check calls `/health`.

Stop the service with:

```powershell
docker compose down
```

Named volumes are retained by that command. Remove them only when intentionally deleting the local vector index and logs:

```powershell
docker compose down -v
```

The Docker image uses `/app/data`, `/app/.chroma`, and `/app/logs` internally. Compose maps Chroma data and logs to named volumes and overrides the local host paths from `.env`.

## Documentation

- [REST API contracts](docs/api.md)
- [Operations and observability](docs/operations.md)
- [Privacy rules](docs/privacy.md)

## API Summary

- `GET /health`: liveness check; does not require an API key.
- `GET /ready`: readiness check for configuration, local data, and Chroma.
- `POST /chat`: validates a question and optional history, retrieves book context, calls the recommendation service, and returns a recommendation with the complete local summary.

All responses include `X-Correlation-ID`. See [REST API contracts](docs/api.md) for request, response, validation, error, and CORS details.

## Troubleshooting

### `Fatal error in launcher` from `uvicorn`

The Windows console launcher may contain an old virtual-environment path if the project was moved. From `backend`, activate the current environment and use:

```powershell
deactivate
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### `WinError 10048` or port already in use

Another API process is already using port `8000`. Stop it with `Ctrl+C`, or select another port with the Uvicorn command shown above.

### `/health` succeeds but `/ready` returns `503`

Check `OPENAI_API_KEY`, the book and filter configuration paths, and Chroma initialization. The response intentionally hides internal details; inspect the application logs using the correlation ID.

### Chroma telemetry override error during ingestion

If ingestion fails with an error similar to:

```text
TypeError: Method capture overrides method from ProductTelemetryClient but does not have @override decorator
```

the custom telemetry implementation in `app/core/noop_chroma_telemetry.py` must decorate its `capture` method with `@override` from the `overrides` package. The current implementation already contains this decorator.

After changing backend source files, rebuild the Docker image because the Compose service copies the source into the image rather than bind-mounting `backend/app`:

```powershell
docker compose build backend
docker compose up -d backend
docker compose exec backend python -m app.scripts.ingest_books
```

Successful repeat ingestion reports the number of added, failed, skipped, and updated books. Chroma telemetry remains disabled through `ANONYMIZED_TELEMETRY=false` and the no-op telemetry implementation configured in `docker-compose.yml`.