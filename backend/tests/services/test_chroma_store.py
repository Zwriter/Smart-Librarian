from pathlib import Path
from typing import Any

import pytest
from app.core.exceptions import RetrievalError
from app.services.chroma_store import ChromaVectorStore


class FakeCollection:
	def __init__(self) -> None:
		self.embedding: list[list[float]] = []
		self.result: dict[str, Any] = {"ids": [[]]}

	def query(self, **kwargs: Any) -> dict[str, Any]:
		self.embedding = kwargs["query_embeddings"]
		return self.result

	def get(self, ids: list[str]) -> dict[str, Any]:
		return {"ids": ids[:1]}

	def upsert(self, **kwargs: Any) -> None:
		self.upserted = kwargs


class FakeChromaClient:
	def __init__(self, collection: FakeCollection) -> None:
		self.collection = collection
		self.collection_name = ""

	def get_or_create_collection(self, name: str) -> FakeCollection:
		self.collection_name = name
		return self.collection


def test_chroma_store_uses_named_collection_and_forwards_query() -> None:
	collection = FakeCollection()
	client = FakeChromaClient(collection)
	store = ChromaVectorStore(Path(".chroma"), "books", client=client)

	result = store.query([0.1, 0.2], top_k=4)

	assert client.collection_name == "books"
	assert collection.embedding == [[0.1, 0.2]]
	assert result == {"ids": [[]]}


def test_chroma_store_wraps_initialization_errors() -> None:
	class FailingClient:
		def get_or_create_collection(self, name: str) -> None:
			raise RuntimeError("unavailable")

	with pytest.raises(RetrievalError, match="Unable to initialize vector store"):
		ChromaVectorStore(Path(".chroma"), "books", client=FailingClient())


def test_chroma_store_upserts_records_and_reports_existing_ids() -> None:
	collection = FakeCollection()
	store = ChromaVectorStore(Path(".chroma"), "books", client=FakeChromaClient(collection))

	existing = store.upsert(
		["book-1", "book-2"],
		["one", "two"],
		[[0.1], [0.2]],
		[{"title": "One"}, {"title": "Two"}],
	)

	assert existing == {"book-1"}
	assert collection.upserted["ids"] == ["book-1", "book-2"]