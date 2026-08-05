import json

import pytest
from app.core.exceptions import (
	FilterConfigurationError,
	InputRejectedError,
	InputValidationError,
)
from app.services.input_filter import InputFilter


def write_filter_config(path, config: object) -> None:
	path.write_text(json.dumps(config), encoding="utf-8")


def test_filter_normalizes_allowed_question(tmp_path) -> None:
	config_path = tmp_path / "filter.json"
	write_filter_config(config_path, {"blocked_terms": [], "blocked_patterns": []})

	result = InputFilter(config_path, max_question_length=100).validate("  Find   a book.  ")

	assert result == "Find a book."


def test_filter_rejects_blocked_term_case_insensitively(tmp_path) -> None:
	config_path = tmp_path / "filter.json"
	write_filter_config(config_path, {"blocked_terms": ["spoiler"], "blocked_patterns": []})

	with pytest.raises(InputRejectedError):
		InputFilter(config_path, max_question_length=100).validate("Contains a SPOILER")


def test_filter_rejects_empty_and_oversized_questions(tmp_path) -> None:
	config_path = tmp_path / "filter.json"
	write_filter_config(config_path, {"blocked_terms": [], "blocked_patterns": []})
	input_filter = InputFilter(config_path, max_question_length=5)

	with pytest.raises(InputValidationError):
		input_filter.validate("   ")
	with pytest.raises(InputValidationError):
		input_filter.validate("123456")


def test_filter_rejects_invalid_pattern_configuration(tmp_path) -> None:
	config_path = tmp_path / "filter.json"
	write_filter_config(config_path, {"blocked_patterns": ["["]})

	with pytest.raises(FilterConfigurationError):
		InputFilter(config_path, max_question_length=100).validate("Question")