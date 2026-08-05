import json
from collections.abc import Callable
from typing import Any

from app.core.exceptions import ToolCallError
from app.services.llm_client import ToolCall

SUMMARY_TOOL_NAME = "get_summary_by_title"


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

		return self._summary_lookup(title.strip())

	@staticmethod
	def _parse_arguments(arguments: str) -> dict[str, Any]:
		try:
			parsed = json.loads(arguments)
		except (json.JSONDecodeError, TypeError) as error:
			raise ToolCallError("Tool arguments must be valid JSON") from error
		if not isinstance(parsed, dict):
			raise ToolCallError("Tool arguments must be a JSON object")
		return parsed