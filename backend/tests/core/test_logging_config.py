import json
import logging
from pathlib import Path

from app.core.logging_config import JsonFormatter, SafeConsoleFormatter, configure_logging


def test_json_formatter_includes_structured_fields() -> None:
	record = logging.LogRecord("app", logging.INFO, "", 0, "ready", (), None)
	record.event = "readiness_check"
	record.correlation_id = "request-1"

	result = json.loads(JsonFormatter().format(record))

	assert result["event"] == "readiness_check"
	assert result["correlation_id"] == "request-1"
	assert result["message"] == "ready"


def test_configure_logging_creates_console_and_rotating_file_handlers(tmp_path: Path) -> None:
	log_path = tmp_path / "logs" / "app.log"
	logger = configure_logging("DEBUG", log_path, 1_000, 2)

	logger.info("configured", extra={"event": "logging_configured"})

	assert log_path.parent.is_dir()
	assert log_path.is_file()
	assert len(logger.handlers) == 2
	assert {type(handler).__name__ for handler in logger.handlers} == {
		"StreamHandler",
		"RotatingFileHandler",
	}
	assert '"event": "logging_configured"' in log_path.read_text(encoding="utf-8")


def test_console_formatter_excludes_exception_content() -> None:
	try:
		raise RuntimeError("private summary must not be displayed")
	except RuntimeError:
		record = logging.LogRecord("app", logging.ERROR, "", 0, "provider failed", (), None)
		record.exc_info = __import__("sys").exc_info()

	result = SafeConsoleFormatter().format(record)

	assert "private summary" not in result
	assert "exception_type=RuntimeError" in result