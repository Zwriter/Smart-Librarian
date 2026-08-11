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
		cached_books = self._repository.get(query)
		if cached_books is not None:
			return cached_books[:limit]

		books = self._client.search_volumes(query, limit)
		self._repository.save(query, books)
		if self._indexer is not None:
			try:
				self._indexer.index(books)
			except (LLMClientError, RetrievalError):
				logging.getLogger(__name__).warning(
					"Unable to index Google Books results; returning metadata only",
					exc_info=True,
				)
		return books