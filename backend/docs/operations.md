# Operations and Observability

## Configuration

Use the repository `.env.example` as the configuration template. Important operational settings include:

- `CHROMA_PERSIST_DIRECTORY`: persistent vector-store location.
- `MAX_REQUEST_BODY_BYTES`: request body limit; default is 100,000 bytes.
- `LOG_LEVEL`: application log threshold.
- `LOG_CONSOLE_ENABLED`: human-readable console destination.
- `LOG_FILE_ENABLED`: sanitized rotating JSON file destination.
- `LOG_FILE_PATH`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`: file rotation and retention controls.
- `LOG_PRIVACY_MODE`: currently must remain `redact`.
- `MODEL_PRICING`: JSON pricing rates in USD per 1,000,000 tokens.

## Health Checks

Use `/health` for container liveness. Use `/ready` for traffic readiness because it checks provider configuration, local data, filter configuration, and Chroma initialization.

## Request Tracing

Read `X-Correlation-ID` from the response and search the JSON logs for the matching `correlation_id`. Typical events are `request_started`, `ai_usage`, `tool_call_started`, `tool_call_completed`, `request_completed`, and `request_usage_aggregated`.

Exception records retain only an exception type. Prompts, completions, user questions, book summaries, tool arguments, and raw provider payloads are excluded.

## Token and Cost Records

`ai_usage` represents one embedding or chat operation. `request_usage_aggregated` combines recorded operations for one request. `estimated_cost` is an estimate based on configured model pricing. If pricing or provider usage is unavailable, `cost_available` is false and `cost_unavailable_reason` explains the missing information.

## Storage and Retention

The Docker Compose workflow persists Chroma data and logs in named volumes. Local logs are diagnostic artifacts, not an audit store. Restrict access to operators, apply deployment-specific collector retention, and do not retain logs indefinitely by default. See [privacy.md](privacy.md) for the full privacy policy.

## Troubleshooting

1. Check `/health` to confirm the process is alive.
2. Check `/ready` to distinguish startup configuration/data failures from liveness failures.
3. Trace the request with `X-Correlation-ID`.
4. Inspect aggregate token and cost fields without expecting prompt or completion content.
5. Run the provider-free observability tests before making external provider calls.