# Smart Librarian Frontend

React, TypeScript, and Vite frontend for the Smart Librarian chat experience.

## Requirements

- Node.js `20.19+` or `22.12+` (required by the Vite version used here)
- npm `10+`
- A running Smart Librarian backend at `http://127.0.0.1:8000`, unless another API URL is configured

The repository does not declare an `engines` field, so these versions are the supported local development baseline rather than an npm-enforced constraint.

Check the installed versions with:

```powershell
node --version
npm --version
```

## Local setup

From this directory, install the frontend dependencies:

```powershell
npm install
```

Start the backend first. Follow [the backend setup guide](../backend/README.md), then confirm it responds at `http://127.0.0.1:8000/health`. The frontend expects the backend to be available before a question is submitted; the page itself can still load while the backend is stopped.

Start the Vite development server:

```powershell
npm run dev
```

Open `http://127.0.0.1:5173/` in a browser. To expose the development server on a different host, pass Vite arguments, for example `npm run dev -- --host 0.0.0.0`.

## Docker Compose

From the repository root, configure the backend `.env` file as described in [the backend setup guide](../backend/README.md), then build and start both services:

```powershell
docker compose up --build
```

Open `http://localhost:8080/`. The frontend is built into a small Nginx image and calls the backend through the browser at `http://localhost:8000`. Compose waits for the backend health check before starting the frontend. Stop the stack with:

```powershell
docker compose down
```

To use a different browser-visible backend address, pass a build argument and rebuild the frontend:

```powershell
docker compose build --build-arg VITE_API_BASE_URL=http://localhost:8001 frontend
docker compose up
```

The API URL is embedded into the static bundle at build time; changing it requires rebuilding the frontend image.

## Configuration

The frontend reads Vite environment variables from the repository root `.env` at build and development-server startup. Set `VITE_API_BASE_URL` when the backend is not using its default URL:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8001"
npm run dev
```

Use the backend origin only, without the `/chat` path or a trailing slash. The client appends `/chat` to this value. Do not put `OPENAI_API_KEY` or any other secret in a `VITE_` variable: Vite exposes `VITE_` values to browser code.
`VITE_MAX_QUESTION_LENGTH` and `VITE_MAX_HISTORY_MESSAGES` control the corresponding browser limits. Keep these aligned with the backend `MAX_QUESTION_LENGTH` and `MAX_HISTORY_MESSAGES` values.

## Frontend-backend communication

The Vite development server uses port `5173`. The client sends an unauthenticated `POST /chat` request to `VITE_API_BASE_URL` with JSON containing:

```json
{
  "question": "A mysterious story with an unforgettable setting.",
  "history": [
    { "role": "user", "content": "I like atmospheric mysteries." },
    { "role": "assistant", "content": "A moody mystery could be a good fit." }
  ]
}
```

Questions are trimmed and limited to 2,000 characters in the UI. The browser sends up to 19 previous messages so the new user message remains within the 20-message history limit. Responses render the recommendation title, author, rationale, and complete summary. See the [backend API contract](../backend/docs/api.md) for the server-side validation and response schema.

The frontend sends no OpenAI credentials. Provider configuration belongs exclusively to the backend.

## Browser-session behavior

Conversation messages and the current recommendation are held in React memory for the active browser tab. They are not written to local storage, cookies, or a database. Refreshing the page, opening a new tab, or closing the tab starts a new conversation. The **Clear shelf** action removes the current messages, question, errors, and recommendation immediately.

The visible conversation is capped at 20 messages. While a request is in progress, the composer is disabled and duplicate submissions are ignored. A failed request keeps its question and history available through **Retry request**.

## Commands

Run these commands from `frontend`:

```powershell
# Start the development server with Vite HMR
npm run dev

# Create the production bundle and run TypeScript project checks
npm run build

# Run Oxlint
npm run lint

# Run the frontend Vitest suite once
npm test

# Run Vitest in watch mode during development
npm run test:watch
```

The test suite uses Vitest, React Testing Library, jsdom, and MSW.

## Troubleshooting

### Backend unavailable

If submitting a question reports that the librarian is unavailable, start the backend and verify its health endpoint:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

If the backend uses another port, set `VITE_API_BASE_URL` and restart Vite. A page reload alone does not reread environment variables.

### CORS errors

The browser origin must be allowed by the backend. For local development, use the documented Vite URL `http://127.0.0.1:5173/` consistently; `localhost` and `127.0.0.1` are different origins. Configure the backend `CORS_ALLOWED_ORIGINS` to include the exact frontend origin, restart the backend, and reload the page.

### Invalid API URL

`VITE_API_BASE_URL` must be an absolute `http` or `https` backend origin, such as `http://127.0.0.1:8000`. Do not set it to `http://127.0.0.1:8000/chat`, a relative path, or a URL with a typo. Correct the variable and restart the Vite process because environment values are embedded when Vite starts or builds.

### Failed build

Run the commands from the `frontend` directory and install dependencies first:

```powershell
npm install
npm run build
```

Read the first TypeScript error in the output; later errors may be follow-on diagnostics. If the dependency tree is incomplete, remove `node_modules` and `package-lock.json`, run `npm install`, and retry. Do not commit generated `dist` output or local environment files.

### Lint or test failures

Run the failing command by itself to isolate the issue:

```powershell
npm run lint
npm test
```

Tests do not require a running backend because API calls are mocked. Browser or integration checks do require the backend and correct CORS configuration.
