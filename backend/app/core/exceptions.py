class BookDataError(RuntimeError):
	"""Raised when the local book data cannot be loaded or validated."""


class BookNotFoundError(LookupError):
	"""Raised when a requested book title is not in the repository."""


class FilterConfigurationError(RuntimeError):
	"""Raised when the input-filter configuration cannot be loaded."""


class InputValidationError(ValueError):
	"""Raised when user input does not meet basic validation requirements."""


class InputRejectedError(ValueError):
	"""Raised when user input matches a configured blocked rule."""


class InputSafetyError(RuntimeError):
	"""Raised when the model-based safety validator cannot return a valid result."""


class IntentClassificationError(RuntimeError):
	"""Raised when the intent classifier cannot return a valid classification."""


class LLMClientError(RuntimeError):
	"""Raised when an LLM provider request fails or returns an unusable response."""


class ToolCallError(RuntimeError):
	"""Raised when an LLM requests an unknown or invalid tool call."""


class RetrievalError(RuntimeError):
	"""Raised when vector retrieval fails or returns invalid data."""


class GoogleBooksError(RuntimeError):
	"""Raised when the Google Books provider cannot return valid data."""


class AuthPersistenceError(RuntimeError):
	"""Raised when private authentication data cannot be persisted safely."""


class ChatServiceError(RuntimeError):
	"""Raised when recommendation orchestration cannot produce a response."""