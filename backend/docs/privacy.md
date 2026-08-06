# Observability Privacy Rules

## Approved Data

Application logs contain operational metadata only: timestamps, levels, logger names, event names, correlation IDs, request method and path, status, duration, AI operation and model names, provider request IDs, token counts, operation counts, and estimated-cost status.

Prompts, raw questions, conversation history, completions, book summaries, tool arguments, and provider request payloads are excluded by default. Identifiers that are not required for operations should be omitted or represented by a non-reversible identifier.

## Redaction and Errors

The safe logging layer redacts API keys, authorization values, credentials, passwords, secrets, and tokens in structured values and recognized message patterns. JSON and console formatters use the same redaction rules. Exception logs contain the exception type only; exception bodies are not emitted because provider and filesystem errors may contain sensitive content.

Logging failures must never replace or mask the original application or provider error. Telemetry emission is best effort and isolated from request handling.

## Retention and Access

- Local logs are written under `backend/logs/` and ignored by Git.
- File output uses UTF-8 rotating logs with the configured maximum file size and backup count.
- Local logs are diagnostic artifacts, not an audit store. Delete them when no longer needed and review them before sharing.
- Production collectors should apply deployment-specific retention and deletion rules; do not retain logs indefinitely by default.
- Restrict local and production log access using least-privilege developer, operator, or service-account roles.
- Do not enable request-body, prompt, completion, tool-argument, or raw provider-payload logging to troubleshoot a request. Reproduce with sanitized fixtures instead.

## Request Tracing

Use the `X-Correlation-ID` response header and matching `correlation_id` field in structured events to follow one request. Correlation IDs identify a request but do not grant access to its content. Usage records expose aggregate token and estimated-cost fields only; unavailable costs are reported explicitly rather than guessed.