import json
from typing import Any, cast

from app.core.exceptions import ChatServiceError
from app.domain.chat_request import ChatRequest
from app.domain.chat_response import ChatResponse
from app.domain.recommendation import Recommendation
from app.services.input_filter import InputFilter
from app.services.llm_client import LLMClient
from app.services.recommendation_prompt import (
	GET_SUMMARY_TOOL,
	build_recommendation_messages,
)
from app.services.retriever import Retriever
from app.services.tool_call_executor import ToolCallExecutor
from pydantic import ValidationError


class ChatService:
	"""Coordinates validation, retrieval, recommendation, and summary lookup."""

	def __init__(
		self,
		input_filter: InputFilter,
		retriever: Retriever,
		llm_client: LLMClient,
		tool_executor: ToolCallExecutor,
	) -> None:
		self._input_filter = input_filter
		self._retriever = retriever
		self._llm_client = llm_client
		self._tool_executor = tool_executor

	def recommend(self, request: ChatRequest) -> ChatResponse:
		question = self._input_filter.validate(request.question)
		retrieved_books = self._retriever.retrieve(question)
		messages = build_recommendation_messages(question, request.history, retrieved_books)

		try:
			completion = self._llm_client.create_chat_completion(
				messages,
				tools=[GET_SUMMARY_TOOL],
			)
			if len(completion.tool_calls) != 1:
				raise ChatServiceError("Recommendation provider must request one summary tool")
			summary = self._tool_executor.execute(completion.tool_calls[0])
			content = completion.content
			if content is None:
				follow_up = self._llm_client.create_chat_completion(
					[
						*messages,
						{
							"role": "system",
							"content": (
								"The summary lookup succeeded. Now return only one JSON object "
								"with string fields title, author, and rationale."
							),
						},
					],
				)
				content = follow_up.content
			if content is None:
				raise ChatServiceError("Recommendation provider returned no recommendation")
			recommendation = self._parse_recommendation(content)
			return ChatResponse(recommendation=recommendation, summary=summary)
		except ChatServiceError:
			raise
		except Exception as error:
			raise ChatServiceError("Unable to complete book recommendation") from error

	@staticmethod
	def _parse_recommendation(content: str) -> Recommendation:
		try:
			payload: Any = json.loads(content)
			if not isinstance(payload, dict):
				raise ChatServiceError("Recommendation must be a JSON object")
			return cast(Recommendation, Recommendation.model_validate(payload))
		except (json.JSONDecodeError, ValidationError) as error:
			raise ChatServiceError("Recommendation provider returned invalid JSON") from error
