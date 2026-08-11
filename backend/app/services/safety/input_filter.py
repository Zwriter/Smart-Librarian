import json
import re
from pathlib import Path

from app.core.exceptions import (
	FilterConfigurationError,
	InputRejectedError,
	InputValidationError,
)


class InputFilter:
	"""Validates and filters user questions using local configuration."""

	def __init__(self, config_path: Path, max_question_length: int) -> None:
		self._config_path = config_path
		self._max_question_length = max_question_length
		self._blocked_terms: tuple[str, ...] | None = None
		self._blocked_patterns: tuple[re.Pattern[str], ...] | None = None

	def validate(self, question: str) -> str:
		normalized_question = " ".join(question.split())
		if not normalized_question:
			raise InputValidationError("Question cannot be empty")
		if len(normalized_question) > self._max_question_length:
			raise InputValidationError("Question exceeds the maximum allowed length")

		blocked_terms, blocked_patterns = self._load_rules()
		question_casefolded = normalized_question.casefold()
		if any(term in question_casefolded for term in blocked_terms):
			raise InputRejectedError("Question contains disallowed content")
		if any(pattern.search(normalized_question) for pattern in blocked_patterns):
			raise InputRejectedError("Question contains disallowed content")

		return normalized_question

	def _load_rules(self) -> tuple[tuple[str, ...], tuple[re.Pattern[str], ...]]:
		if self._blocked_terms is not None and self._blocked_patterns is not None:
			return self._blocked_terms, self._blocked_patterns

		try:
			data = json.loads(self._config_path.read_text(encoding="utf-8"))
		except (OSError, json.JSONDecodeError) as error:
			raise FilterConfigurationError(
				f"Unable to load filter configuration from {self._config_path}"
			) from error

		if not isinstance(data, dict):
			raise FilterConfigurationError("Filter configuration must be a JSON object")

		blocked_terms = self._read_string_list(data, "blocked_terms")
		blocked_patterns = self._read_string_list(data, "blocked_patterns")
		try:
			compiled_patterns = tuple(
				re.compile(pattern, re.IGNORECASE) for pattern in blocked_patterns
			)
		except re.error as error:
			raise FilterConfigurationError(
				"Filter configuration contains an invalid pattern"
			) from error

		self._blocked_terms = tuple(term.casefold() for term in blocked_terms)
		self._blocked_patterns = compiled_patterns
		return self._blocked_terms, self._blocked_patterns

	@staticmethod
	def _read_string_list(data: dict[str, object], key: str) -> list[str]:
		value = data.get(key, [])
		if not isinstance(value, list) or any(
			not isinstance(item, str) or not item.strip() for item in value
		):
			raise FilterConfigurationError(f"{key} must be a list of non-empty strings")
		return [item.strip() for item in value]
