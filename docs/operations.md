# Operations

## Request Diagnosis

Use this sequence when diagnosing a request:

1. Check `/health` to confirm that the process is alive.
2. Check `/ready` for configuration, data, or Chroma readiness failures.
3. Capture `X-Correlation-ID` from the response.
4. Search structured logs for the matching `correlation_id`.
5. Inspect aggregate token and cost fields without expecting prompt or completion content.

The API does not return secrets, prompts, completions, summaries, tool arguments, raw provider payloads, or filesystem paths in error responses.

## Catalogue Ingestion

Run repeatable ingestion from the `backend` directory:

```powershell
python -m app.scripts.ingest_books
```

Ingestion validates `data/book_summaries.json`, creates embeddings, and upserts stable document IDs into the configured Chroma collection. It requires an OpenAI key and a writable Chroma directory.

For Compose:

```powershell
docker compose exec backend python -m app.scripts.ingest_books
```

The Compose Chroma volume persists the resulting index across container restarts.

## Logging and Privacy

Structured logs include operational metadata such as timestamps, event names, correlation IDs, paths, status codes, durations, model names, token counts, and estimated-cost status. By default they exclude questions, conversation history, prompts, completions, summaries, tool arguments, raw provider payloads, and secrets.

Treat local logs as diagnostic artifacts, restrict access, and apply deployment-specific retention. See [the privacy policy](../backend/docs/privacy.md) for the complete logging and retention rules.

## Updating Backend Images

Compose copies backend source into the image rather than bind-mounting `backend/app`. Rebuild after backend source changes:

```powershell
docker compose build backend
docker compose up -d backend
docker compose exec backend python -m app.scripts.ingest_books
```
