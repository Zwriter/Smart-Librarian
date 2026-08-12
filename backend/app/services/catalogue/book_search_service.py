import re
import unicodedata

from app.core.exceptions import BookNotFoundError
from app.domain.book import Book
from app.services.catalogue.book_repository import BookRepository
from app.services.google_books.google_books_search import GoogleBooksSearchService


class BookSearchService:
	"""Resolves an exact book title from the local catalogue or Google Books."""

	def __init__(
		self,
		book_repository: BookRepository,
		google_books_search: GoogleBooksSearchService,
	) -> None:
		self._book_repository = book_repository
		self._google_books_search = google_books_search

	def find_by_title(self, title: str) -> Book:
		"""Return the requested title from local data or the external provider."""
		try:
			return self._book_repository.get_by_title(title)
		except BookNotFoundError:
			pass

		books = self._google_books_search.search(title, 10)

		requested_title = self._normalize_title(title)
		matched_book = next(
			(book for book in books if self._normalize_title(book.title) == requested_title),
			None,
		)
		if matched_book is None:
			matched_book = next(
				(
					book
					for book in books
					if self._singularize_title(self._normalize_title(book.title))
					== self._singularize_title(requested_title)
				),
				None,
			)
		if matched_book is None:
			raise BookNotFoundError(
				"The book you are trying to access is not available."
			)

		return Book(
			title=matched_book.title,
			author=", ".join(matched_book.authors) or "Unknown author",
			summary=matched_book.description or "No description available from Google Books.",
			description=matched_book.description,
			metadata={"source": "google_books", "volume_id": matched_book.volume_id},
		)

	@staticmethod
	def _normalize_title(title: str) -> str:
		decomposed = unicodedata.normalize("NFKD", title.casefold())
		without_diacritics = "".join(
			character for character in decomposed if not unicodedata.combining(character)
		)
		return re.sub(r"[^\w]+", " ", without_diacritics, flags=re.ASCII).strip()

	@staticmethod
	def _singularize_title(title: str) -> str:
		words = title.split()
		if words and len(words[-1]) > 3 and words[-1].endswith("s"):
			words[-1] = words[-1][:-1]
		return " ".join(words)
