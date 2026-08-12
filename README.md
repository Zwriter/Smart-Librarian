<h1 align="center"> Smart Librarian AI-RAG </h1>


## Contents

- [Local Development](#local-development)
- [Docker Compose](#docker-compose)
- [Documentation](#documentation)

## Overview

Smart Librarian is a full-stack book recommendation application. The React frontend sends natural-language questions to a FastAPI backend, which combines input filtering, semantic retrieval from a Chroma catalogue, OpenAI recommendations, local summaries, and Google Books fallback search.

The chatbox can:

- Recommend books from the **local catalogue** using **natural-language questions**.
- Refine recommendations by mood, genre, theme, or reading preferences.
- Search and prioritize books in the **language of the prompt** or a **language explicitly specified by the user**.
- Retrieve complete summaries for books in the local catalogue.
- Search **Google Books** when the local catalogue does not have enough relevant results.
- Continue conversations with bounded message history.

## Local Development

### Requirements

- Python 3.11+
- Node.js 20.19+ or 22.12+
- npm 10+
- An OpenAI API key

Create the local environment file from the template and set `OPENAI_API_KEY`:

```powershell
Copy-Item .env.example .env
```

Install dependencies once:

```powershell
Set-Location backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Location ..\frontend
npm install
Set-Location ..
npm install
```

Start both development servers from the repository root:

```powershell
npm run dev:servers
```

The frontend is available at `http://127.0.0.1:5173/` and the backend at `http://127.0.0.1:8000/`. To start them individually, follow the backend and frontend guides below.

Before making recommendations, ingest the local catalogue:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m app.scripts.ingest_books
```

## Docker Compose

Configure `.env` with `OPENAI_API_KEY`, then run from the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The frontend is available at `http://localhost:8080/` and the backend at `http://localhost:8000/`. Chroma data and backend logs are persisted in named volumes.

Stop the stack while retaining its volumes:

```powershell
docker compose down
```

The complete Compose configuration and volume guidance are in [docs/docker-compose.md](docs/docker-compose.md).

## Documentation

- [Backend](backend/README.md)
- [Frontend](frontend/README.md)
- [REST API Contract](backend/docs/api.md)
- [Architecture](docs/architecture.md)
- [Docker Compose](docs/docker-compose.md)
- [Operations & Observability](docs/operations.md)
- [Backend Privacy Rules](backend/docs/privacy.md)
- [Troubleshooting](docs/troubleshooting.md)