from app.services.llm_client import TokenUsage
from app.services.usage_aggregation import UsageAggregator


def test_usage_aggregator_calculates_chat_cost_and_totals() -> None:
	aggregator = UsageAggregator({"chat-model": {"input": 1.0, "output": 2.0}})

	aggregator.record(
		TokenUsage(
			operation="chat",
			model="chat-model",
			prompt_tokens=1_000_000,
			completion_tokens=500_000,
			total_tokens=1_500_000,
		)
	)

	summary = aggregator.summary()

	assert summary.input_tokens == 1_000_000
	assert summary.output_tokens == 500_000
	assert summary.total_tokens == 1_500_000
	assert summary.operation_count == 1
	assert summary.estimated_cost == 2.0
	assert summary.cost_available is True


def test_usage_aggregator_handles_unknown_model_without_blocking() -> None:
	aggregator = UsageAggregator({})

	aggregator.record(TokenUsage(operation="embedding", model="unknown", total_tokens=10))

	summary = aggregator.summary()

	assert summary.total_tokens == 10
	assert summary.estimated_cost is None
	assert summary.cost_available is False
	assert "unknown" in (summary.cost_unavailable_reason or "")