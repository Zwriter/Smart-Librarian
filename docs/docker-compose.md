# Docker Compose

The Compose stack builds the FastAPI backend and Nginx frontend. It waits for the backend health check before starting the frontend and persists Chroma data and backend logs in named volumes.

## Start

From the repository root:

```powershell
Copy-Item backend/.env.example backend/.env
# Set OPENAI_API_KEY in backend/.env before starting the stack.
docker compose up --build
```

The application is available at `http://localhost:8080/`. The API is available at `http://localhost:8000/`.

## Configuration

The backend `.env` supplies runtime secrets and provider settings to the backend. The root `.env` is reserved for shared browser-safe `VITE_*` settings. Compose overrides container paths and local browser origins:

- `BOOK_DATA_PATH=/app/data/book_summaries.json`
- `FILTER_CONFIG_PATH=/app/data/filter_config.json`
- `CHROMA_PERSIST_DIRECTORY=/app/.chroma`
- `LOG_FILE_PATH=/app/logs/app.log`
- `CORS_ALLOWED_ORIGINS` includes the local Vite and Compose frontend origins
- `ANONYMIZED_TELEMETRY=false`

The frontend receives `VITE_API_BASE_URL=http://localhost:8000` at image build time. To use another browser-visible backend address, rebuild the frontend:

```powershell
docker compose build --build-arg VITE_API_BASE_URL=http://localhost:8001 frontend
docker compose up
```

The API URL is embedded in the static frontend bundle, so changing it requires a frontend rebuild.

## Data and Logs

Named volumes are retained by `docker compose down`:

```powershell
docker compose down
```

Remove the local Chroma index and logs only when intentionally resetting persisted data:

```powershell
docker compose down -v
```

The Compose volumes are:

- `chroma-data`, mounted at `/app/.chroma`
- `backend-logs`, mounted at `/app/logs`
