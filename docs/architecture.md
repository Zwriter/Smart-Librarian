# Architecture

Smart Librarian is a full-stack book recommendation application. The React frontend sends questions to the FastAPI backend, which validates input, retrieves catalogue context, calls OpenAI, and returns a recommendation with its summary.

## Request Flow

```text
Browser
  |
  | POST /chat
  v
React + TypeScript + Vite (local) / Nginx (Compose)
  |
  | CORS-enabled HTTP API
  v
FastAPI backend
  |
  +--> Input filtering and domain validation
  +--> Chroma vector store <--> OpenAI embeddings
  +--> Retriever and recommendation prompt <--> OpenAI chat model
  +--> Local summary tool and book repository
  +--> Google Books cache and fallback search
  +--> Correlation-aware structured logging and usage aggregation
```

The normal recommendation path is:

1. The frontend submits a question and conversation history.
2. FastAPI validates the request and enforces body and history limits.
3. The input filter rejects unsupported or unsafe content.
4. The retriever searches the ingested Chroma catalogue.
5. Google Books is used only when local results are absent or insufficient.
6. The recommendation service asks the configured chat model to select a book.
7. The summary tool resolves complete summaries from the local catalogue.
8. The API returns the response with an `X-Correlation-ID`.

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
  docs/           Backend API, operations, and privacy documentation
  tests/          Backend unit and API tests
frontend/
  src/
    components/   Conversation, composer, recommendation, and error UI
    hooks/        Chat state and API orchestration
    services/     Browser API client and tests
    styles/       Application stylesheets
  public/         Static frontend assets
  tests/          Frontend component and integration tests
docs/             Project architecture, Compose, operations, and troubleshooting
docker-compose.yml
.env.example
```
