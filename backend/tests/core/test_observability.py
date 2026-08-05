import json
import logging
from pathlib import Path

from app.core.logging_config import JsonFormatter, configure_logging
from app.services.llm_client import TokenUsage
from app.services.usage_aggregation import UsageAggregator


def test_observability_records_approved_usage_fields_without_provider_calls() -> None:
	aggregator = UsageAggregator(
		{
			"chat-model": {"input": 1.0, "output": 2.0},
		}
	)
	aggregator.record(
		TokenUsage(
			operation="chat",
			model="chat-model",
			prompt_tokens=10,
			completion_tokens=5,
			total_tokens=15,
		)
	)

	summary = aggregator.summary()

	assert summary.input_tokens == 10
	assert summary.output_tokens == 5
	assert summary.total_tokens == 15
	assert summary.estimated_cost == 0.00002


def test_observability_json_event_is_machine_readable(tmp_path: Path) -> None:
	log_path = tmp_path / "observability" / "app.log"
	logger = configure_logging(
		"INFO",
		log_path,
		10_000,
		1,
		log_console_enabled=False,
	)

	logger.info(
		"AI usage recorded",
		extra={
			"event": "ai_usage",
			"correlation_id": "request-1",
			"operation": "chat",
			"model": "chat-model",
			"prompt_tokens": 10,
			"completion_tokens": 5,
			"total_tokens": 15,
		},
	)
	for handler in logger.handlers:
		handler.flush()

	record = json.loads(log_path.read_text(encoding="utf-8"))

	assert record["event"] == "ai_usage"
	assert record["correlation_id"] == "request-1"
	assert record["total_tokens"] == 15
	assert "prompt" not in record
	assert isinstance(JsonFormatter(), logging.Formatter)