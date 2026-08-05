import json
import logging
import sys

from app.core.logging_config import JsonFormatter
from app.core.safe_logging import redact_value, safe_log


def test_json_formatter_redacts_secrets_and_excludes_exception_content() -> None:
	try:
		raise RuntimeError("private book summary and sk-secret-value")
	except RuntimeError:
		record = logging.LogRecord(
			"app",
			logging.ERROR,
			"",
			0,
			"Authorization: Bearer sk-secret-value api_key=another-secret",
			(),
			None,
		)
		record.exc_info = sys.exc_info()
		record.api_key = "another-secret"

	result = json.loads(JsonFormatter().format(record))

	assert "sk-secret-value" not in json.dumps(result)
	assert "private book summary" not in json.dumps(result)
	assert result["exception_type"] == "RuntimeError"
	assert "api_key" not in result


def test_safe_log_does_not_raise_when_logger_fails() -> None:
	class BrokenLogger:
		def log(self, *_args: object, **_kwargs: object) -> None:
			raise OSError("log sink unavailable")

	try:
		raise ValueError("original application error")
	except ValueError:
		safe_log(BrokenLogger(), logging.ERROR, "failure", exc_info=True)  # type: ignore[arg-type]

	assert True


def test_redact_value_handles_nested_sensitive_fields() -> None:
	value = redact_value({"request": {"authorization": "Bearer secret"}, "title": "visible"})

	assert value == {
		"request": {"authorization": "[REDACTED]"},
		"title": "visible",
	}