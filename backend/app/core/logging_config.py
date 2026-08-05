import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.safe_logging import redact_text, redact_value

LOGGER_NAME = "app"


def _exception_type_name(record: logging.LogRecord) -> str:
	if record.exc_info is None or record.exc_info[0] is None:
		return "unknown"
	return record.exc_info[0].__name__


class JsonFormatter(logging.Formatter):
	"""Formats application records as compact JSON for file ingestion."""

	def format(self, record: logging.LogRecord) -> str:
		payload: dict[str, Any] = {
			"timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
			"level": record.levelname,
			"logger": record.name,
			"message": redact_text(record.getMessage()),
		}
		for field in (
			"event",
			"environment",
			"service_version",
			"correlation_id",
			"method",
			"path",
			"status_code",
			"duration_ms",
			"operation",
			"model",
			"prompt_tokens",
			"completion_tokens",
			"total_tokens",
			"provider_request_id",
			"tool_call_depth",
			"input_tokens",
			"output_tokens",
			"cost_available",
			"estimated_cost",
			"operation_count",
			"cost_unavailable_reason",
		):
			value = getattr(record, field, None)
			if value is not None:
				payload[field] = redact_value(value, field)
		if record.exc_info:
			payload["exception_type"] = _exception_type_name(record)
		return json.dumps(payload, ensure_ascii=True, sort_keys=True)


class SafeConsoleFormatter(logging.Formatter):
	"""Formats console records without exposing exception bodies."""

	def format(self, record: logging.LogRecord) -> str:
		message = (
			f"{self.formatTime(record)} {record.levelname} {record.name} "
			f"{redact_text(record.getMessage())}"
		)
		if record.exc_info:
			message += f" exception_type={_exception_type_name(record)}"
		return message


def configure_logging(
	log_level: str,
	log_file_path: Path,
	log_max_bytes: int,
	log_backup_count: int,
	log_console_enabled: bool = True,
	log_file_enabled: bool = True,
	) -> logging.Logger:
	"""Configure the application logger and return it."""
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(log_level.upper())
	logger.propagate = False
	if log_file_enabled:
		log_file_path.parent.mkdir(parents=True, exist_ok=True)
	for handler in list(logger.handlers):
		handler.close()
		logger.removeHandler(handler)

	if log_console_enabled:
		console_handler = logging.StreamHandler()
		console_handler.setFormatter(SafeConsoleFormatter())
		logger.addHandler(console_handler)
	if log_file_enabled:
		file_handler = RotatingFileHandler(
			log_file_path,
			maxBytes=log_max_bytes,
			backupCount=log_backup_count,
			encoding="utf-8",
		)
		file_handler.setFormatter(JsonFormatter())
		logger.addHandler(file_handler)
	return logger