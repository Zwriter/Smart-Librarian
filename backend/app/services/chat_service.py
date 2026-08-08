import json
import re
from collections.abc import Sequence
from typing import Any, cast

from app.core.exceptions import BookNotFoundError, ChatServiceError
from app.domain.chat_request import ChatRequest
from app.domain.chat_response import ChatResponse
from app.domain.conversation_message import ConversationMessage
from app.domain.recommendation import Recommendation
from app.domain.retrieved_book import RetrievedBook
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

	CAPABILITIES_MESSAGE = (
		"Hello. I can recommend books from the local catalogue, summarize books I "
		"know, and help you narrow a choice by mood, genre, or theme."
	)

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
		intent_question = request.question
		if re.fullmatch(
			r"(?:hi|hello|hey|good morning|good afternoon|good evening)[!. ]*",
			intent_question.casefold(),
		):
			return ChatResponse(message=self.CAPABILITIES_MESSAGE)
		retrieved_books = self._retriever.retrieve(question)
		ambiguous = self._is_ambiguous_request(intent_question, retrieved_books)
		previous_titles = self._previously_recommended_titles(request.history)
		prompt_books = self._exclude_previous_books(retrieved_books, previous_titles, ambiguous)
		messages = build_recommendation_messages(
			question,
			request.history,
			prompt_books,
			ambiguous=ambiguous,
		previous_titles=previous_titles,
		)
		try:
			completion = self._llm_client.create_chat_completion(
				messages,
				tools=() if ambiguous else [GET_SUMMARY_TOOL],
			)
			if not completion.tool_calls:
				if completion.content is None:
					raise ChatServiceError("Recommendation provider returned no response")
				return self._parse_non_recommendation(completion.content)
			if len(completion.tool_calls) != 1:
				raise ChatServiceError("Recommendation provider must request one summary tool")
			try:
				summary = self._tool_executor.execute(completion.tool_calls[0])
			except BookNotFoundError:
				return ChatResponse(message="I don't know that book from the local catalogue.")
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
			return ChatResponse(
				recommendation=recommendation,
				summary=self._compact_summary(summary),
			)
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

	@staticmethod
	def _parse_non_recommendation(content: str) -> ChatResponse:
		try:
			payload: Any = json.loads(content)
			if not isinstance(payload, dict):
				raise ChatServiceError("Non-recommendation response must be a JSON object")
			return cast(ChatResponse, ChatResponse.model_validate(payload))
		except (json.JSONDecodeError, ValidationError, TypeError) as error:
			raise ChatServiceError("Recommendation provider returned invalid JSON") from error

	@staticmethod
	def _compact_summary(summary: str) -> str:
		return " ".join(summary.split()[:40])

	@staticmethod
	def _is_ambiguous_request(
		question: str, retrieved_books: Sequence[RetrievedBook]
	) -> bool:
		question_text = question.casefold()
		mentions_catalogue_title = any(
			retrieved.book.title.casefold() in question_text for retrieved in retrieved_books
		)
		return not mentions_catalogue_title and bool(
			re.search(
				r"\b(?:something|anything|a book|some books|give me|recommend)\b",
				question_text,
			)
		)

	@staticmethod
	def _previously_recommended_titles(
		history: Sequence[ConversationMessage],
	) -> set[str]:
		return {
			message.content.casefold()
			for message in history
			if message.role == "assistant"
		}

	@staticmethod
	def _exclude_previous_books(
		retrieved_books: Sequence[RetrievedBook],
		previous_messages: set[str],
		ambiguous: bool,
	) -> tuple[RetrievedBook, ...]:
		if not ambiguous or not previous_messages:
			return tuple(retrieved_books)
		fresh_books = tuple(
			book
			for book in retrieved_books
			if not any(book.book.title.casefold() in message for message in previous_messages)
		)
		if len(fresh_books) >= 3:
			return fresh_books
		return tuple(retrieved_books)
