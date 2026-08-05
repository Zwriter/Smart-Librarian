from types import SimpleNamespace

import pytest
from app.core.exceptions import LLMClientError
from app.services.llm_client import OpenAIClient


class FakeEmbeddingClient:
	def __init__(self, response: object) -> None:
		self.embeddings = SimpleNamespace(create=lambda **kwargs: response)


class FakeChatClient:
	def __init__(self, response: object) -> None:
		self.chat = SimpleNamespace(
			completions=SimpleNamespace(create=lambda **kwargs: response)
		)


def test_openai_client_creates_embedding_with_configured_model() -> None:
	response = SimpleNamespace(
		data=[SimpleNamespace(embedding=[0.1, 0.2])],
		usage=SimpleNamespace(prompt_tokens=4, total_tokens=4),
		id="embedding-1",
	)
	client = OpenAIClient(
		api_key="test-key",
		chat_model="chat-model",
		embedding_model="embedding-model",
		client=FakeEmbeddingClient(response),
	)

	result = client.create_embedding("find a mystery")

	assert result.embedding == [0.1, 0.2]
	assert result.usage is not None
	assert result.usage.prompt_tokens == 4


def test_openai_client_maps_chat_content_and_tool_calls() -> None:
	message = SimpleNamespace(
		content="I recommend Frankenstein.",
		tool_calls=[
			SimpleNamespace(
				id="call-1",
				function=SimpleNamespace(
					name="get_summary_by_title",
					arguments='{"title":"Frankenstein"}',
				),
			)
		],
	)
	response = SimpleNamespace(
		choices=[SimpleNamespace(message=message)],
		usage=SimpleNamespace(prompt_tokens=8, completion_tokens=5, total_tokens=13),
		id="chat-1",
	)
	client = OpenAIClient(
		api_key="test-key",
		chat_model="chat-model",
		embedding_model="embedding-model",
		client=FakeChatClient(response),
	)

	result = client.create_chat_completion([{"role": "user", "content": "Recommend a book."}])

	assert result.content == "I recommend Frankenstein."
	assert result.tool_calls[0].name == "get_summary_by_title"
	assert result.usage is not None
	assert result.usage.total_tokens == 13


def test_openai_client_allows_missing_usage() -> None:
	response = SimpleNamespace(data=[SimpleNamespace(embedding=[0.1])])
	client = OpenAIClient(
		api_key="test-key",
		chat_model="chat-model",
		embedding_model="embedding-model",
		client=FakeEmbeddingClient(response),
	)

	assert client.create_embedding("query").usage is None


def test_openai_client_wraps_provider_errors() -> None:
	class FailingClient:
		embeddings = SimpleNamespace(
			create=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("offline"))
		)

	client = OpenAIClient(
		api_key="test-key",
		chat_model="chat-model",
		embedding_model="embedding-model",
		client=FailingClient(),
	)

	with pytest.raises(LLMClientError, match="Embedding request failed"):
		client.create_embedding("query")