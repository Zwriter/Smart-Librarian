import hashlib
from dataclasses import dataclass
from typing import Protocol

from app.core.exceptions import LLMClientError, RetrievalError
from app.domain.book import Book
from app.services.book_repository import BookRepository
from app.services.llm_client import LLMClient


class IngestionStore(Protocol):
	def upsert(
		self,
		ids: list[str],
		documents: list[str],
		embeddings: list[list[float]],
		metadatas: list[dict[str, str]],
	) -> set[str]:
		...


@dataclass(frozen=True)
class IngestionReport:
	added: int
	updated: int
	skipped: int
	failed: int


class IngestionService:
	"""Embeds the validated catalogue and upserts it into the vector store."""

	def __init__(
		self,
		repository: BookRepository,
		llm_client: LLMClient,
		vector_store: IngestionStore,
	) -> None:
		self._repository = repository
		self._llm_client = llm_client
		self._vector_store = vector_store

	def ingest(self) -> IngestionReport:
		books = self._repository.list_books()
		ids: list[str] = []
		documents: list[str] = []
		embeddings: list[list[float]] = []
		metadatas: list[dict[str, str]] = []

		for book in books:
			ids.append(self._document_id(book))
			documents.append(self._document(book))
			metadatas.append(self._metadata(book))
			try:
				embeddings.append(self._llm_client.create_embedding(documents[-1]).embedding)
			except Exception as error:
				raise LLMClientError("Unable to embed book data") from error

		try:
			existing = self._vector_store.upsert(ids, documents, embeddings, metadatas)
		except RetrievalError:
			raise
		except Exception as error:
			raise RetrievalError("Unable to persist book embeddings") from error

		return IngestionReport(
			added=len(set(ids) - existing),
			updated=len(set(ids) & existing),
			skipped=0,
			failed=0,
		)

	@staticmethod
	def _document_id(book: Book) -> str:
		return hashlib.sha256(book.title.casefold().encode("utf-8")).hexdigest()

	@staticmethod
	def _document(book: Book) -> str:
		description = book.description or ""
		return (
			f"Title: {book.title}\nAuthor: {book.author}\nSummary: {book.summary}"
			f"\nDescription: {description}"
		)

	@staticmethod
	def _metadata(book: Book) -> dict[str, str]:
		return {
			"title": book.title,
			"author": book.author,
			"summary": book.summary,
			"description": book.description or "",
		}