from contextvars import ContextVar, Token
from uuid import UUID, uuid4

CORRELATION_HEADER = "X-Correlation-ID"
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
	return _correlation_id.get()


def create_correlation_id(candidate: str | None) -> str:
	if candidate:
		try:
			return str(UUID(candidate))
		except ValueError:
			pass
	return str(uuid4())


def set_correlation_id(value: str) -> Token[str | None]:
	return _correlation_id.set(value)


def reset_correlation_id(token: Token[str | None]) -> None:
	_correlation_id.reset(token)