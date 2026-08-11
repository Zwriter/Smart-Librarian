from __future__ import annotations

from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from app.services.llm.llm_client import TokenUsage

DEFAULT_MODEL_PRICING: dict[str, dict[str, float]] = {
	"gpt-4o-mini": {"input": 0.15, "output": 0.60},
	"text-embedding-3-small": {"embedding": 0.02},
}


@dataclass(frozen=True)
class UsageCost:
	amount: float | None
	available: bool
	reason: str | None = None


@dataclass(frozen=True)
class UsageSummary:
	input_tokens: int
	output_tokens: int
	total_tokens: int
	operation_count: int
	estimated_cost: float | None
	cost_available: bool
	cost_unavailable_reason: str | None = None


class UsageAggregator:
	"""Aggregates provider-neutral usage for one request or operation."""

	def __init__(self, pricing: Mapping[str, Mapping[str, float]]) -> None:
		self._pricing = pricing
		self._records: list[tuple[TokenUsage, UsageCost]] = []

	def record(self, usage: TokenUsage) -> UsageCost:
		cost = self._estimate_cost(usage)
		self._records.append((usage, cost))
		return cost

	def summary(self) -> UsageSummary:
		input_tokens = sum(record.prompt_tokens or 0 for record, _ in self._records)
		output_tokens = sum(record.completion_tokens or 0 for record, _ in self._records)
		total_tokens = sum(
			record.total_tokens
			if record.total_tokens is not None
			else (record.prompt_tokens or 0) + (record.completion_tokens or 0)
			for record, _ in self._records
		)
		unavailable = [cost.reason for _, cost in self._records if not cost.available]
		amounts = [cost.amount for _, cost in self._records if cost.amount is not None]
		return UsageSummary(
			input_tokens=input_tokens,
			output_tokens=output_tokens,
			total_tokens=total_tokens,
			operation_count=len(self._records),
			estimated_cost=round(sum(amounts), 8) if not unavailable else None,
			cost_available=not unavailable,
			cost_unavailable_reason=unavailable[0] if unavailable else None,
		)

	def _estimate_cost(self, usage: TokenUsage) -> UsageCost:
		model_pricing = self._pricing.get(usage.model)
		if model_pricing is None:
			return UsageCost(None, False, f"No pricing configured for model '{usage.model}'")
		if usage.operation == "embedding":
			rate = model_pricing.get("embedding")
			tokens = usage.prompt_tokens or usage.total_tokens
		else:
			rate = model_pricing.get("input")
			output_rate = model_pricing.get("output")
			if rate is None or output_rate is None:
				return UsageCost(
					None,
					False,
					f"Incomplete pricing configured for model '{usage.model}'",
				)
			if tokens := usage.prompt_tokens:
				input_cost = tokens * rate / 1_000_000
			else:
				input_cost = 0.0
			completion_cost = (usage.completion_tokens or 0) * output_rate / 1_000_000
			return UsageCost(input_cost + completion_cost, True)
		if rate is None or tokens is None:
			return UsageCost(None, False, f"Usage data unavailable for model '{usage.model}'")
		return UsageCost(tokens * rate / 1_000_000, True)


_current_aggregator: ContextVar[UsageAggregator | None] = ContextVar(
	"usage_aggregator", default=None
)


def set_usage_aggregator(aggregator: UsageAggregator) -> object:
	return _current_aggregator.set(aggregator)


def reset_usage_aggregator(token: object) -> None:
	_current_aggregator.reset(token)  # type: ignore[arg-type]


def record_usage(usage: TokenUsage) -> UsageCost | None:
	aggregator = _current_aggregator.get()
	return aggregator.record(usage) if aggregator else None