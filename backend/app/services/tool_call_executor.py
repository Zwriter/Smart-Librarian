import json
import logging
from collections.abc import Callable
from typing import Any

from app.core.correlation import get_correlation_id
from app.core.exceptions import ToolCallError
from app.services.llm_client import ToolCall

SUMMARY_TOOL_NAME = "get_summary_by_title"
logger = logging.getLogger("app.ai")


class ToolCallExecutor:
	"""Validates and dispatches the narrowly scoped tools exposed to the LLM."""

	def __init__(self, summary_lookup: Callable[[str], str], max_call_depth: int = 1) -> None:
		if max_call_depth < 1:
			raise ValueError("max_call_depth must be positive")
		self._summary_lookup = summary_lookup
		self._max_call_depth = max_call_depth

	def execute(self, tool_call: ToolCall, call_depth: int = 0) -> str:
		if call_depth >= self._max_call_depth:
			raise ToolCallError("Tool-call depth limit exceeded")
		if tool_call.name != SUMMARY_TOOL_NAME:
			raise ToolCallError(f"Unknown tool: {tool_call.name}")

		arguments = self._parse_arguments(tool_call.arguments)
		title = arguments.get("title")
		if not isinstance(title, str) or not title.strip():
			raise ToolCallError("Tool arguments require a non-empty title")
		if set(arguments) != {"title"}:
			raise ToolCallError("Tool arguments contain unknown fields")

		logger.info(
			"Tool call started",
			extra={
				"event": "tool_call_started",
				"correlation_id": get_correlation_id(),
				"operation": tool_call.name,
				"tool_call_depth": call_depth,
			},
		)
		try:
			result = self._summary_lookup(title.strip())
		except Exception:
			logger.exception(
				"Tool call failed",
				extra={
					"event": "tool_call_failed",
					"correlation_id": get_correlation_id(),
					"operation": tool_call.name,
					"tool_call_depth": call_depth,
				},
			)
			raise
		logger.info(
			"Tool call completed",
			extra={
				"event": "tool_call_completed",
				"correlation_id": get_correlation_id(),
				"operation": tool_call.name,
				"tool_call_depth": call_depth,
			},
		)
		return result

	@staticmethod
	def _parse_arguments(arguments: str) -> dict[str, Any]:
		try:
			parsed = json.loads(arguments)
		except (json.JSONDecodeError, TypeError) as error:
			raise ToolCallError("Tool arguments must be valid JSON") from error
		if not isinstance(parsed, dict):
			raise ToolCallError("Tool arguments must be a JSON object")
		return parsed