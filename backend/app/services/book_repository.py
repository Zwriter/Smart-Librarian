import json
from pathlib import Path

from app.core.exceptions import BookDataError, BookNotFoundError
from app.domain.book import Book
from pydantic import ValidationError


class BookRepository:
	"""Provides validated access to the local book catalogue."""

	def __init__(self, data_path: Path) -> None:
		self._data_path = data_path
		self._books: tuple[Book, ...] | None = None

	def list_books(self) -> tuple[Book, ...]:
		if self._books is None:
			self._books = self._load_books()

		return self._books

	def get_by_title(self, title: str) -> Book:
		normalized_title = title.strip().casefold()
		if not normalized_title:
			raise BookNotFoundError("The book you are trying to access is not available.")

		for book in self.list_books():
			if book.title.casefold() == normalized_title:
				return book

		raise BookNotFoundError("The book you are trying to access is not available.")

	def get_summary_by_title(self, title: str) -> str:
		return self.get_by_title(title).summary

	def _load_books(self) -> tuple[Book, ...]:
		try:
			data = json.loads(self._data_path.read_text(encoding="utf-8"))
		except (OSError, json.JSONDecodeError) as error:
			raise BookDataError(f"Unable to load book data from {self._data_path}") from error

		if not isinstance(data, list):
			raise BookDataError("Book data must be a JSON array")

		books: list[Book] = []
		seen_titles: set[str] = set()
		for index, item in enumerate(data):
			try:
				book = Book.model_validate(item)
			except ValidationError as error:
				raise BookDataError(f"Invalid book record at index {index}") from error

			normalized_title = book.title.casefold()
			if normalized_title in seen_titles:
				raise BookDataError(f"Duplicate book title: {book.title}")

			seen_titles.add(normalized_title)
			books.append(book)

		return tuple(books)