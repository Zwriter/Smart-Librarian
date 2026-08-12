import json
import re
from collections.abc import Sequence
from typing import Any, Protocol, cast

from app.core.exceptions import (
	BookNotFoundError,
	ChatServiceError,
	GoogleBooksError,
	InputSafetyError,
	IntentClassificationError,
)
from app.domain.book import Book
from app.domain.chat_request import ChatRequest
from app.domain.chat_response import ChatResponse
from app.domain.conversation_intent import ConversationIntent
from app.domain.conversation_message import ConversationMessage
from app.domain.google_book import GoogleBook
from app.domain.recommendation import Recommendation
from app.domain.retrieved_book import RetrievedBook
from app.services.catalogue.book_search_service import BookSearchService
from app.services.conversation.intent_classifier import IntentClassifier
from app.services.conversation.recommendation_prompt import (
	GET_SUMMARY_TOOL,
	build_recommendation_messages,
)
from app.services.llm.llm_client import LLMClient
from app.services.retrieval.retriever import Retriever
from app.services.safety.input_filter import InputFilter
from app.services.safety.input_safety_validator import InputSafetyValidator
from app.services.tools.tool_call_executor import ToolCallExecutor
from pydantic import ValidationError


class GoogleBooksSearch(Protocol):
	def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		...


class ChatService:
	"""Coordinates validation, retrieval, recommendation, and summary lookup."""

	CAPABILITIES_MESSAGE = (
		"Hello. I can recommend books from the local catalogue, summarize books I "
		"know, and help you narrow a choice by mood, genre, or theme."
	)
	SAFETY_REJECTION_MESSAGE = (
		"I can help with books, but I cannot process profanity or obscene content."
	)
	def __init__(
		self,
		input_filter: InputFilter,
		retriever: Retriever,
		llm_client: LLMClient,
		tool_executor: ToolCallExecutor,
		intent_classifier: IntentClassifier | None = None,
		input_safety_validator: InputSafetyValidator | None = None,
		google_books_search: GoogleBooksSearch | None = None,
		book_search: BookSearchService | None = None,
	) -> None:
		self._input_filter = input_filter
		self._retriever = retriever
		self._llm_client = llm_client
		self._tool_executor = tool_executor
		self._intent_classifier = intent_classifier
		self._input_safety_validator = input_safety_validator
		self._google_books_search = google_books_search
		self._book_search = book_search

	def recommend(self, request: ChatRequest) -> ChatResponse:
		question = self._input_filter.validate(request.question)
		if self._input_safety_validator is not None:
			try:
				safety = self._input_safety_validator.validate(question, request.history)
			except InputSafetyError as error:
				raise ChatServiceError("Unable to validate chat input") from error
			if not safety.allowed:
				return ChatResponse(message=self.SAFETY_REJECTION_MESSAGE)
		intent: ConversationIntent | None = None
		if self._intent_classifier is not None:
			try:
				intent = self._intent_classifier.classify(question, request.history)
			except IntentClassificationError as error:
				raise ChatServiceError("Unable to classify chat request") from error
			if intent.intent in {"greeting", "capabilities", "general_conversation"}:
				return ChatResponse(message=self.CAPABILITIES_MESSAGE)
		intent_question = request.question
		try:
			resolved_book = self._resolve_requested_book(intent)
		except BookNotFoundError:
			resolved_book = None
		except GoogleBooksError:
			return ChatResponse(
				message="I couldn't look up that book right now. Please try again shortly."
			)
		retrieved_books = (
			(self._as_retrieved_book_data(resolved_book),)
			if resolved_book is not None
			else self._retrieve_local_books(question, intent)
		)
		external_books = self._retrieve_external_books(
			question,
			retrieved_books,
			intent,
		)
		if external_books:
			retrieved_books = tuple(self._as_retrieved_book(book) for book in external_books)
		external_context = bool(external_books) or any(
			book.book.metadata.get("source") == "google_books" for book in retrieved_books
		)
		ambiguous = self._is_ambiguous_request(intent_question, retrieved_books, intent)
		previous_titles = self._previously_recommended_titles(request.history)
		prompt_books = self._exclude_previous_books(retrieved_books, previous_titles, ambiguous)
		messages = build_recommendation_messages(
			question,
			request.history,
			prompt_books,
			ambiguous=ambiguous,
			previous_titles=previous_titles,
			response_language=intent.response_language if intent is not None else None,
		)
		allow_summary_tool = self._allows_summary_tool(intent, retrieved_books, external_context)
		try:
			completion = self._llm_client.create_chat_completion(
				messages,
				tools=[GET_SUMMARY_TOOL] if allow_summary_tool and not ambiguous else (),
			)
			if not completion.tool_calls:
				if completion.content is None:
					raise ChatServiceError("Recommendation provider returned no response")
				if external_context and not ambiguous and external_books:
					return self._parse_external_recommendation(completion.content, external_books)
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

	def _retrieve_external_books(
		self,
		question: str,
		local_books: Sequence[RetrievedBook],
		intent: ConversationIntent | None,
	) -> tuple[GoogleBook, ...]:
		if self._google_books_search is None or not self._should_search_external(
			local_books, intent
		):
			return ()
		try:
			query = (
				f"intitle:{intent.book_title}"
				if intent is not None and intent.book_title
				else question
			)
			books = self._google_books_search.search(query, 3)
			if intent is not None and intent.response_language:
				localized_books = tuple(
					book
					for book in books
					if book.language == intent.response_language
				)
				if localized_books:
					return localized_books
			return books
		except GoogleBooksError:
			return ()

	def _resolve_requested_book(self, intent: ConversationIntent | None) -> Book | None:
		if self._book_search is None or intent is None or intent.book_title is None:
			return None
		return self._book_search.find_by_title(intent.book_title)

	@staticmethod
	def _as_retrieved_book_data(book: Book) -> RetrievedBook:
		return RetrievedBook(
			book=book,
			document_id=f"title:{book.title.casefold()}",
			relevance_score=0,
		)

	def _retrieve_local_books(
		self,
		question: str,
		intent: ConversationIntent | None,
	) -> tuple[RetrievedBook, ...]:
		if intent is not None and not intent.requires_retrieval:
			return ()
		return tuple(self._retriever.retrieve(question))

	@staticmethod
	def _allows_summary_tool(
		intent: ConversationIntent | None,
		retrieved_books: Sequence[RetrievedBook],
		external_context: bool,
	) -> bool:
		if external_context:
			return False
		if intent is None:
			return True
		if not intent.requires_summary_tool or intent.book_title is None:
			return False
		return any(
			book.book.title.casefold() == intent.book_title.casefold()
			and book.book.metadata.get("source") != "google_books"
			for book in retrieved_books
		) and all(
			book.book.metadata.get("source") != "google_books"
			for book in retrieved_books
		)

	@staticmethod
	def _should_search_external(
		local_books: Sequence[RetrievedBook],
		intent: ConversationIntent | None,
	) -> bool:
		if not local_books:
			return intent is None or intent.book_title is not None
		if any(
			book.book.metadata.get("source") == "google_books"
			for book in local_books
		):
			return True
		if intent is not None and not intent.requires_retrieval:
			return False
		if intent is None or intent.book_title is None:
			return False
		return not any(
			book.book.title.casefold() == intent.book_title.casefold()
			for book in local_books
		)

	@staticmethod
	def _as_retrieved_book(book: GoogleBook) -> RetrievedBook:
		return RetrievedBook(
			book=Book(
				title=book.title,
				author=", ".join(book.authors) or "Unknown author",
				summary=book.description or "No description available from Google Books.",
				description=book.description,
				metadata={"source": "google_books", "volume_id": book.volume_id},
			),
			document_id=f"google-volume:{book.volume_id}",
			relevance_score=0,
		)

	@classmethod
	def _parse_external_recommendation(
		cls,
		content: str,
		books: Sequence[GoogleBook],
	) -> ChatResponse:
		try:
			recommendation = cls._parse_recommendation(content)
		except ChatServiceError:
			book = cls._select_external_book(books)
			description = book.description or "No description available from Google Books."
			return ChatResponse(
				recommendation=Recommendation(
					title=book.title,
					author=", ".join(book.authors) or "Unknown author",
					rationale=cls._compact_summary(description),
					published_date=book.published_date,
					publisher=book.publisher,
					language=book.language,
				),
				summary=description,
			)
		matching_books = tuple(
			book for book in books if book.title.casefold() == recommendation.title.casefold()
		)
		matched_book = cls._select_external_book(matching_books) if matching_books else None
		if matched_book is None:
			raise ChatServiceError("Recommendation provider returned an unknown external book")
		description = matched_book.description or "No description available from Google Books."
		recommendation = recommendation.model_copy(
			update={
				"published_date": matched_book.published_date,
				"publisher": matched_book.publisher,
				"language": matched_book.language,
			}
		)
		return ChatResponse(
			recommendation=recommendation,
			summary=description,
		)

	@staticmethod
	def _select_external_book(books: Sequence[GoogleBook]) -> GoogleBook:
		if not books:
			raise ChatServiceError("Google Books returned no matching book")
		return max(
			books,
			key=lambda book: (
				bool(book.published_date and re.fullmatch(r"\d{4}", book.published_date)),
				bool(book.description),
				bool(book.authors),
				bool(book.publisher),
			),
		)

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
		question: str,
		retrieved_books: Sequence[RetrievedBook],
		intent: ConversationIntent | None,
	) -> bool:
		if intent is not None:
			return intent.intent == "recommendation" and intent.book_title is None
		return not retrieved_books

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
