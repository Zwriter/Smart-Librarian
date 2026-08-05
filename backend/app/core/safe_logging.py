"""Failure-isolated logging helpers for operational telemetry."""

import logging
import re
from collections.abc import Mapping
from typing import Any

_SECRET_KEYS = {
	"api_key",
	"authorization",
	"credential",
	"password",
	"secret",
	"token",
}
_SECRET_ASSIGNMENT = re.compile(
	r"(?i)(api[_-]?key|authorization|credential|password|secret|token)\s*[:=]\s*([^\s,;]+)"
)


def redact_value(value: Any, key: str | None = None) -> Any:
	if key and any(secret in key.lower() for secret in _SECRET_KEYS):
		return "[REDACTED]"
	if isinstance(value, Mapping):
		return {
			str(item_key): redact_value(item_value, str(item_key))
			for item_key, item_value in value.items()
		}
	if isinstance(value, list | tuple):
		return [redact_value(item) for item in value]
	if isinstance(value, str):
		return redact_text(value)
	return value


def redact_text(value: str) -> str:
	redacted = _SECRET_ASSIGNMENT.sub(r"\1=[REDACTED]", value)
	redacted = re.sub(r"(?i)\b(Bearer|Basic)\s+\S+", r"\1 [REDACTED]", redacted)
	redacted = re.sub(r"(?<![\w-])sk-\S+", "sk-[REDACTED]", redacted)
	return redacted


def safe_log(
	logger: logging.Logger,
	level: int,
	message: str,
	*,
	extra: Mapping[str, Any] | None = None,
	exc_info: bool = False,
) -> None:
	"""Emit telemetry without masking the operation that produced it."""
	try:
		safe_extra = {
			key: redact_value(value, key)
			for key, value in (extra or {}).items()
		}
		logger.log(level, redact_text(message), extra=safe_extra, exc_info=exc_info)
	except Exception:
		return