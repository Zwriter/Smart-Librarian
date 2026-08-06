# Smart Librarian Frontend

React, TypeScript, and Vite frontend for the Smart Librarian chat experience.

## API contract

The Vite development server uses port `5173`. Set `VITE_API_BASE_URL` to the backend base URL; it defaults to `http://127.0.0.1:8000`. The client sends `POST /chat` with a trimmed question of 1-2,000 characters and up to 20 history messages. Each message has a non-empty `content` value and a `role` of `user` or `assistant`.

Responses render `recommendation.title`, `recommendation.author`, `recommendation.rationale`, and `summary`. OpenAI credentials are never configured or sent by the frontend.

Run the frontend with `npm run dev`, validate with `npm test`, and build with `npm run build`.

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
