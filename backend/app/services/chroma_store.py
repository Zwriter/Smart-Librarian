from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import chromadb
from app.core.exceptions import RetrievalError


class ChromaVectorStore:
	"""Persistent ChromaDB adapter for the configured book collection."""

	def __init__(
		self,
		persist_directory: Path,
		collection_name: str,
		client: Any | None = None,
	) -> None:
		try:
			self._client = client or chromadb.PersistentClient(path=str(persist_directory))
			self._collection = self._client.get_or_create_collection(name=collection_name)
		except Exception as error:
			raise RetrievalError("Unable to initialize vector store") from error

	def query(self, embedding: Sequence[float], top_k: int) -> dict[str, Any]:
		if top_k < 1:
			raise ValueError("top_k must be positive")
		try:
			result = self._collection.query(
				query_embeddings=[list(embedding)],
				n_results=top_k,
			)
			return cast(dict[str, Any], result)
		except Exception as error:
			raise RetrievalError("Vector store query failed") from error

	def upsert(
		self,
		ids: Sequence[str],
		documents: Sequence[str],
		embeddings: Sequence[Sequence[float]],
		metadatas: Sequence[dict[str, str]],
	) -> set[str]:
		try:
			existing = self._collection.get(ids=list(ids)).get("ids", [])
			self._collection.upsert(
				ids=list(ids),
				documents=list(documents),
				embeddings=[list(embedding) for embedding in embeddings],
				metadatas=list(metadatas),
			)
			return {item for item in existing if isinstance(item, str)}
		except Exception as error:
			raise RetrievalError("Vector store upsert failed") from error