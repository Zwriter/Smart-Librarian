from app.services.book_repository import BookRepository


class SummaryTool:
	"""Application-facing adapter for complete local book summaries."""

	def __init__(self, book_repository: BookRepository) -> None:
		self._book_repository = book_repository

	def get_summary_by_title(self, title: str) -> str:
		return self._book_repository.get_summary_by_title(title)
