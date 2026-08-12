import logging

from app.core.exceptions import LLMClientError, RetrievalError
from app.domain.google_book import GoogleBook
from app.services.google_books.google_books_client import GoogleBooksClient
from app.services.google_books.google_books_indexer import GoogleBooksIndexer
from app.services.google_books.google_books_repository import GoogleBooksRepository


class GoogleBooksSearchService:
	"""Searches the cache first and stores provider results for later requests."""

	def __init__(
		self,
		client: GoogleBooksClient,
		repository: GoogleBooksRepository,
		indexer: GoogleBooksIndexer | None = None,
	) -> None:
		self._client = client
		self._repository = repository
		self._indexer = indexer

	def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		exact_title = self._exact_title_query(query)
		cached_books = self._repository.get(query)
		if cached_books is not None:
			cached_matches = self._filter_exact_title(cached_books, exact_title)
			if exact_title is None or cached_matches:
				self._index_best_effort(cached_matches)
				return cached_matches[:limit]

		provider_limit = max(limit, 10) if exact_title is not None else limit
		books = self._client.search_volumes(query, provider_limit)
		self._repository.save(query, books)
		matched_books = self._filter_exact_title(books, exact_title)
		self._index_best_effort(matched_books)
		return matched_books

	@classmethod
	def _filter_exact_title(
		cls,
		books: tuple[GoogleBook, ...],
		exact_title: str | None,
	) -> tuple[GoogleBook, ...]:
		if exact_title is None:
			return books
		normalized_title = cls._normalize_title(exact_title)
		return tuple(
			book for book in books if cls._normalize_title(book.title) == normalized_title
		)

	@staticmethod
	def _exact_title_query(query: str) -> str | None:
		prefix = "intitle:"
		if not query.casefold().startswith(prefix):
			return None
		title = query[len(prefix):].strip()
		return title or None

	@staticmethod
	def _normalize_title(title: str) -> str:
		return " ".join(title.strip().casefold().split())

	def _index_best_effort(self, books: tuple[GoogleBook, ...]) -> None:
		if self._indexer is None:
			return
		try:
			self._indexer.index(books)
		except (LLMClientError, RetrievalError):
			logging.getLogger(__name__).warning(
				"Unable to index Google Books results; returning metadata only",
				exc_info=True,
			)