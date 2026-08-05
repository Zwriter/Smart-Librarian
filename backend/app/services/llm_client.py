import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.correlation import get_correlation_id
from app.core.exceptions import LLMClientError
from app.core.safe_logging import safe_log
from app.services.usage_aggregation import record_usage
from openai import OpenAI


@dataclass(frozen=True)
class ToolCall:
	"""Provider-neutral representation of a requested function call."""

	id: str
	name: str
	arguments: str


@dataclass(frozen=True)
class TokenUsage:
	"""Provider-neutral token accounting for one AI operation."""

	operation: str
	model: str
	prompt_tokens: int | None = None
	completion_tokens: int | None = None
	total_tokens: int | None = None
	provider_request_id: str | None = None


@dataclass(frozen=True)
class EmbeddingResult:
	"""Provider-neutral embedding response and optional usage metadata."""

	embedding: list[float]
	usage: TokenUsage | None = None


@dataclass(frozen=True)
class ChatCompletionResult:
	"""Provider-neutral chat response and optional usage metadata."""

	content: str | None
	tool_calls: tuple[ToolCall, ...] = ()
	usage: TokenUsage | None = None


class LLMClient(Protocol):
	"""Abstraction for embedding and chat operations."""

	def create_embedding(self, text: str) -> EmbeddingResult:
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

	def create_embedding(self, text: str) -> EmbeddingResult:
		try:
			response = self._client.embeddings.create(model=self._embedding_model, input=text)
			usage = self._extract_usage(response, "embedding", self._embedding_model)
			self._log_usage(usage)
			return EmbeddingResult(embedding=list(response.data[0].embedding), usage=usage)
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
			usage = self._extract_usage(response, "chat", self._chat_model)
			self._log_usage(usage)
			return ChatCompletionResult(content=message.content, tool_calls=tool_calls, usage=usage)
		except (AttributeError, IndexError, TypeError, ValueError) as error:
			raise LLMClientError("Chat provider returned an invalid response") from error
		except Exception as error:
			raise LLMClientError("Chat request failed") from error

	@staticmethod
	def _extract_usage(response: Any, operation: str, model: str) -> TokenUsage | None:
		provider_usage = getattr(response, "usage", None)
		if provider_usage is None:
			return None
		return TokenUsage(
			operation=operation,
			model=model,
			prompt_tokens=getattr(provider_usage, "prompt_tokens", None),
			completion_tokens=getattr(provider_usage, "completion_tokens", None),
			total_tokens=getattr(provider_usage, "total_tokens", None),
			provider_request_id=getattr(response, "id", None),
		)

	@staticmethod
	def _log_usage(usage: TokenUsage | None) -> None:
		if usage is None:
			return
		safe_log(
			logging.getLogger("app.ai"),
			logging.INFO,
			"AI usage recorded",
			extra={
				"event": "ai_usage",
				"correlation_id": get_correlation_id(),
				"operation": usage.operation,
				"model": usage.model,
				"prompt_tokens": usage.prompt_tokens,
				"completion_tokens": usage.completion_tokens,
				"total_tokens": usage.total_tokens,
				"provider_request_id": usage.provider_request_id,
			},
		)
		record_usage(usage)
