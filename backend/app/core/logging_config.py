import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOGGER_NAME = "app"


class JsonFormatter(logging.Formatter):
	"""Formats application records as compact JSON for file ingestion."""

	def format(self, record: logging.LogRecord) -> str:
		payload: dict[str, Any] = {
			"timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
			"level": record.levelname,
			"logger": record.name,
			"message": record.getMessage(),
		}
		for field in ("event", "environment", "service_version", "correlation_id"):
			value = getattr(record, field, None)
			if value is not None:
				payload[field] = value
		if record.exc_info:
			payload["exception"] = self.formatException(record.exc_info)
		return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def configure_logging(
	log_level: str,
	log_file_path: Path,
	log_max_bytes: int,
	log_backup_count: int,
	) -> logging.Logger:
	"""Configure the application logger and return it."""
	logger = logging.getLogger(LOGGER_NAME)
	logger.setLevel(log_level.upper())
	logger.propagate = False
	log_file_path.parent.mkdir(parents=True, exist_ok=True)
	for handler in logger.handlers:
		handler.close()
		logger.removeHandler(handler)

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(
		logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
	)
	file_handler = RotatingFileHandler(
		log_file_path,
		maxBytes=log_max_bytes,
		backupCount=log_backup_count,
		encoding="utf-8",
	)
	file_handler.setFormatter(JsonFormatter())
	logger.addHandler(console_handler)
	logger.addHandler(file_handler)
	return logger