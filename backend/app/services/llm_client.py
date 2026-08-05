from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.exceptions import LLMClientError
from openai import OpenAI


@dataclass(frozen=True)
class ToolCall:
	"""Provider-neutral representation of a requested function call."""

	id: str
	name: str
	arguments: str


@dataclass(frozen=True)
class ChatCompletionResult:
	"""Provider-neutral chat response used by application services."""

	content: str | None
	tool_calls: tuple[ToolCall, ...] = ()


class LLMClient(Protocol):
	"""Abstraction for embedding and chat operations."""

	def create_embedding(self, text: str) -> list[float]:
		...

	def create_chat_completion(
		self,
		messages: Sequence[Mapping[str, str]],
		tools: Sequence[Mapping[str, Any]] = (),
	) -> ChatCompletionResult:
		...


class OpenAIClient:
	"""OpenAI SDK adapter kept behind the provider-neutral LLM interface."""

	def __init__(
		self,
		api_key: str,
		chat_model: str,
		embedding_model: str,
		client: Any | None = None,
	) -> None:
		self._client = client or OpenAI(api_key=api_key)
		self._chat_model = chat_model
		self._embedding_model = embedding_model

	def create_embedding(self, text: str) -> list[float]:
		try:
			response = self._client.embeddings.create(model=self._embedding_model, input=text)
			return list(response.data[0].embedding)
		except (AttributeError, IndexError, TypeError, ValueError) as error:
			raise LLMClientError("Embedding provider returned an invalid response") from error
		except Exception as error:
			raise LLMClientError("Embedding request failed") from error

	def create_chat_completion(
		self,
		messages: Sequence[Mapping[str, str]],
		tools: Sequence[Mapping[str, Any]] = (),
	) -> ChatCompletionResult:
		try:
			request: dict[str, Any] = {
				"model": self._chat_model,
				"messages": list(messages),
			}
			if tools:
				request["tools"] = list(tools)
			response = self._client.chat.completions.create(**request)
			message = response.choices[0].message
			tool_calls = tuple(
				ToolCall(
					id=tool_call.id,
					name=tool_call.function.name,
					arguments=tool_call.function.arguments,
				)
				for tool_call in (message.tool_calls or [])
			)
			return ChatCompletionResult(content=message.content, tool_calls=tool_calls)
		except (AttributeError, IndexError, TypeError, ValueError) as error:
			raise LLMClientError("Chat provider returned an invalid response") from error
		except Exception as error:
			raise LLMClientError("Chat request failed") from error
