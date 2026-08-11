from collections.abc import Sequence
from typing import Protocol

from app.core.exceptions import LLMClientError, RetrievalError
from app.domain.google_book import GoogleBook
from app.services.llm_client import LLMClient


class GoogleBooksIndexStore(Protocol):
	def existing_ids(self, ids: Sequence[str]) -> set[str]:
		...

	def upsert(
		self,
		ids: Sequence[str],
		documents: Sequence[str],
		embeddings: Sequence[Sequence[float]],
		metadatas: Sequence[dict[str, str]],
	) -> set[str]:
		...


class GoogleBooksIndexer:
	"""Embeds and stores new Google Books records in a dedicated collection."""

	def __init__(self, llm_client: LLMClient, vector_store: GoogleBooksIndexStore) -> None:
		self._llm_client = llm_client
		self._vector_store = vector_store

	def index(self, books: Sequence[GoogleBook]) -> None:
		ids = [self._document_id(book) for book in books]
		existing_ids = self._vector_store.existing_ids(ids)
		new_books = [book for book, document_id in zip(books, ids, strict=True) if document_id not in existing_ids]
		if not new_books:
			return

		documents = [self._document(book) for book in new_books]
		try:
			embeddings = [self._llm_client.create_embedding(document).embedding for document in documents]
		except Exception as error:
			raise LLMClientError("Unable to embed Google Books data") from error

		try:
			self._vector_store.upsert(
				[self._document_id(book) for book in new_books],
				documents,
				embeddings,
				[self._metadata(book) for book in new_books],
			)
		except RetrievalError:
			raise
		except Exception as error:
			raise RetrievalError("Unable to persist Google Books embeddings") from error

	@staticmethod
	def _document_id(book: GoogleBook) -> str:
		return f"google-volume:{book.volume_id}"

	@staticmethod
	def _document(book: GoogleBook) -> str:
		authors = ", ".join(book.authors) or "Unknown author"
		return f"Title: {book.title}\nAuthor: {authors}\nDescription: {book.description or ''}"

	@staticmethod
	def _metadata(book: GoogleBook) -> dict[str, str]:
		return {
			"source": "google_books",
			"volume_id": book.volume_id,
			"title": book.title,
			"author": ", ".join(book.authors),
			"description": book.description or "",
		}