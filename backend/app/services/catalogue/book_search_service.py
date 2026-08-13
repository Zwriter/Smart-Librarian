import re
import unicodedata

from app.core.exceptions import BookNotFoundError
from app.domain.book import Book
from app.domain.google_book import GoogleBook
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

	def find_by_title(self, title: str, required_metadata: str | None = None) -> Book:
		"""Return the requested title from local data or the external provider."""
		try:
			local_book = self._book_repository.get_by_title(title)
			if required_metadata is None or self._has_metadata(local_book, required_metadata):
				return local_book
		except BookNotFoundError:
			pass

		books = self._google_books_search.search(f"intitle:{title}", 10)

		requested_title = self._normalize_title(title)
		exact_matches = tuple(
			book for book in books if self._normalize_title(book.title) == requested_title
		)
		matched_book = self._select_match(exact_matches, required_metadata)
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
			metadata={
				"source": "google_books",
				"volume_id": matched_book.volume_id,
				**(
					{"published_date": matched_book.published_date}
					if matched_book.published_date
					else {}
				),
				**({"language": matched_book.language} if matched_book.language else {}),
			},
		)

	@staticmethod
	def _select_match(
		books: tuple[GoogleBook, ...], required_metadata: str | None
	) -> GoogleBook | None:
		if not books:
			return None
		if required_metadata == "language":
			with_language = tuple(book for book in books if book.language)
			if with_language:
				return with_language[0]
		if required_metadata == "description":
			return max(books, key=BookSearchService._full_description_quality)
		if required_metadata == "resume":
			return max(books, key=BookSearchService._description_quality)
		return max(books, key=BookSearchService._description_quality)

	@staticmethod
	def _full_description_quality(book: GoogleBook) -> tuple[int, int, int]:
		description = book.description or ""
		return (bool(description), len(description), bool(book.authors))

	@staticmethod
	def _description_quality(book: GoogleBook) -> tuple[int, int, int, int, int]:
		description = book.description or ""
		length = len(description)
		return (
			bool(description),
			int(80 <= length <= 600),
			-abs(length - 300),
			bool(book.authors),
			bool(book.published_date),
		)

	@staticmethod
	def _has_metadata(book: Book, metadata_kind: str) -> bool:
		if metadata_kind == "author":
			return bool(book.author.strip())
		if metadata_kind == "resume":
			return bool(book.summary.strip())
		if metadata_kind == "description":
			return bool(book.description and book.description.strip())
		return bool(book.metadata.get(metadata_kind) or book.metadata.get("published_date"))

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
