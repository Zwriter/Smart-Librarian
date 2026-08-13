from typing import Any

import pytest
from app.core.exceptions import RetrievalError
from app.services.llm.llm_client import EmbeddingResult
from app.services.retrieval.retriever import Retriever


class FakeLLMClient:
	def __init__(self) -> None:
		self.queries: list[str] = []

	def create_embedding(self, text: str) -> EmbeddingResult:
		self.queries.append(text)
		return EmbeddingResult([0.1, 0.2])


class FakeVectorStore:
	def __init__(self, result: dict[str, Any]) -> None:
		self.result = result
		self.embeddings: list[float] = []
		self.top_k = 0

	def query(self, embedding: list[float], top_k: int) -> dict[str, Any]:
		self.embeddings = embedding
		self.top_k = top_k
		return self.result


def test_retriever_embeds_question_and_maps_ranked_books() -> None:
	llm_client = FakeLLMClient()
	vector_store = FakeVectorStore(
		{
			"ids": [["dune"]],
			"documents": [["A desert epic."]],
			"metadatas": [
				[
					{
						"title": "Dune",
						"author": "Frank Herbert",
						"summary": "A desert epic.",
					}
				]
			],
			"distances": [[1.0]],
		}
	)

	books = Retriever(llm_client, vector_store, top_k=3).retrieve("desert adventure")

	assert llm_client.queries == ["desert adventure"]
	assert vector_store.embeddings == [0.1, 0.2]
	assert vector_store.top_k == 3
	assert books[0].book.title == "Dune"
	assert books[0].relevance_score == 0.5


def test_retriever_supports_legacy_metadata_without_summary() -> None:
	result = {
		"ids": [["google-volume:dune"]],
		"documents": [["Title: Dune"]],
		"metadatas": [[
			{"title": "Dune", "author": "Frank Herbert", "description": "A desert epic."}
		]],
		"distances": [[0.1]],
	}

	books = Retriever._map_results(result)

	assert books[0].book.summary == "A desert epic."


def test_retriever_normalizes_flattened_google_books_metadata() -> None:
	result = {
		"ids": [["google-volume:dune"]],
		"documents": [["Title: Dune"]],
		"metadatas": [[
			{
				"title": "Dune",
				"author": "Frank Herbert",
				"description": "A desert epic.",
				"source": "google_books",
				"volume_id": "dune",
				"language": "en",
			}
		]],
		"distances": [[0.1]],
	}

	books = Retriever._map_results(result)

	assert books[0].book.metadata == {
		"source": "google_books",
		"volume_id": "dune",
		"language": "en",
	}


def test_retriever_returns_empty_tuple_for_empty_collection() -> None:
	result = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

	books = Retriever(FakeLLMClient(), FakeVectorStore(result), top_k=5).retrieve("question")

	assert books == ()


def test_retriever_rejects_mismatched_vector_results() -> None:
	result = {
		"ids": [["dune"]],
		"documents": [],
		"metadatas": [[]],
		"distances": [[]],
	}

	with pytest.raises(RetrievalError, match="mismatched result lengths"):
		Retriever(FakeLLMClient(), FakeVectorStore(result), top_k=5).retrieve("question")