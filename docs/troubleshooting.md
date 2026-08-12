# Troubleshooting

## `Fatal error in launcher` from Uvicorn

A moved virtual environment can leave a stale Windows console launcher. From `backend`, activate the current environment and use the module form:

```powershell
deactivate
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Port Already in Use

Stop the process using port `8000`, or start the backend on another port and update `VITE_API_BASE_URL` before starting the frontend:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

## `/health` Succeeds but `/ready` Returns `503`

Check `OPENAI_API_KEY`, the book and filter configuration paths, and Chroma initialization. The response intentionally hides internal details; inspect application logs using the correlation ID.

## Chroma Telemetry Override Error

If ingestion reports an error similar to:

```text
TypeError: Method capture overrides method from ProductTelemetryClient but does not have @override decorator
```

check `backend/app/core/noop_chroma_telemetry.py`. Its `capture` method must use `@override` from the `overrides` package. The Compose runtime also sets `ANONYMIZED_TELEMETRY=false`.

## Frontend Backend or CORS Errors

Confirm that the backend responds at `/health`, then verify that `VITE_API_BASE_URL` is an absolute backend origin without `/chat` or a trailing slash. For local development, use one exact browser origin consistently: `localhost` and `127.0.0.1` are different origins. Add that origin to the backend `CORS_ALLOWED_ORIGINS` and restart both servers.

Frontend environment values are read when Vite starts or builds, so restart Vite after changing them.
