from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from app.core.exceptions import RetrievalError
from app.domain.book import Book
from app.domain.retrieved_book import RetrievedBook
from app.services.llm_client import LLMClient


class VectorStore(Protocol):
	"""Provider-neutral interface for nearest-neighbor document search."""

	def query(self, embedding: Sequence[float], top_k: int) -> Mapping[str, Any]:
		...


class Retriever:
	"""Embeds a question and maps vector-store results to domain books."""

	def __init__(self, llm_client: LLMClient, vector_store: VectorStore, top_k: int) -> None:
		if top_k < 1:
			raise ValueError("top_k must be positive")
		self._llm_client = llm_client
		self._vector_store = vector_store
		self._top_k = top_k

	def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
		try:
			embedding = self._llm_client.create_embedding(question)
			result = self._vector_store.query(embedding.embedding, self._top_k)
			return self._map_results(result)
		except RetrievalError:
			raise
		except Exception as error:
			raise RetrievalError("Vector retrieval failed") from error

	@staticmethod
	def _map_results(result: Mapping[str, Any]) -> tuple[RetrievedBook, ...]:
		ids = Retriever._read_result_list(result, "ids")
		documents = Retriever._read_result_list(result, "documents")
		metadatas = Retriever._read_result_list(result, "metadatas")
		distances = Retriever._read_result_list(result, "distances")

		if not ids:
			return ()
		if not (len(ids) == len(documents) == len(metadatas) == len(distances)):
			raise RetrievalError("Vector store returned mismatched result lengths")

		books: list[RetrievedBook] = []
		for document_id, document, metadata, distance in zip(
			ids, documents, metadatas, distances, strict=True
		):
			if not isinstance(document_id, str) or not isinstance(document, str):
				raise RetrievalError("Vector store returned invalid document data")
			if not isinstance(metadata, dict):
				raise RetrievalError("Vector store returned invalid metadata")
			if not isinstance(distance, int | float) or distance < 0:
				raise RetrievalError("Vector store returned invalid distance")

			try:
				book = Book.model_validate(metadata)
				books.append(
					RetrievedBook(
						book=book,
						document_id=document_id,
						relevance_score=1 / (1 + distance),
					)
				)
			except (TypeError, ValueError) as error:
				raise RetrievalError("Vector store returned invalid book metadata") from error

		return tuple(books)

	@staticmethod
	def _read_result_list(result: Mapping[str, Any], key: str) -> list[Any]:
		value = result.get(key, [])
		if not isinstance(value, list):
			raise RetrievalError(f"Vector store result field '{key}' must be a list")
		if value and isinstance(value[0], list):
			value = value[0]
		if not isinstance(value, list):
			raise RetrievalError(f"Vector store result field '{key}' must be a list")
		return value
