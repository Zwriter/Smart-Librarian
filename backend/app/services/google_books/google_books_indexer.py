from collections.abc import Sequence
from typing import Protocol

from app.core.exceptions import LLMClientError, RetrievalError
from app.domain.google_book import GoogleBook
from app.services.llm.llm_client import LLMClient


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

	def update_metadata(
		self,
		ids: Sequence[str],
		metadatas: Sequence[dict[str, str]],
	) -> None:
		...


class GoogleBooksIndexer:
	"""Embeds and stores new Google Books records in a dedicated collection."""

	def __init__(self, llm_client: LLMClient, vector_store: GoogleBooksIndexStore) -> None:
		self._llm_client = llm_client
		self._vector_store = vector_store

	def index(self, books: Sequence[GoogleBook]) -> None:
		unique_books = self._unique_books(books)
		if not unique_books:
			return
		ids = [self._document_id(book) for book in unique_books]
		existing_ids = self._vector_store.existing_ids(ids)
		if existing_ids:
			existing_books = [
				book
				for book, document_id in zip(unique_books, ids, strict=True)
				if document_id in existing_ids
			]
			self._vector_store.update_metadata(
				[self._document_id(book) for book in existing_books],
				[self._metadata(book) for book in existing_books],
			)
		new_books = [
			book
			for book, document_id in zip(unique_books, ids, strict=True)
			if document_id not in existing_ids
		]
		if not new_books:
			return

		documents = [self._document(book) for book in new_books]
		try:
			embeddings = [
				self._llm_client.create_embedding(document).embedding
				for document in documents
			]
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
	def _unique_books(books: Sequence[GoogleBook]) -> tuple[GoogleBook, ...]:
		unique_books: dict[str, GoogleBook] = {}
		for book in books:
			unique_books.setdefault(book.volume_id, book)
		return tuple(unique_books.values())

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
			"summary": book.description or "No description available from Google Books.",
			"published_date": book.published_date or "",
			"publisher": book.publisher or "",
			"language": book.language or "",
		}