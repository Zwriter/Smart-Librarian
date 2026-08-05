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