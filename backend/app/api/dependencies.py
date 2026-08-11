from functools import lru_cache
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
	from app.domain.chat_request import ChatRequest
	from app.domain.chat_response import ChatResponse
	from app.domain.google_book import GoogleBook
	from app.services.chat_service import ChatService
	from app.services.google_books_client import GoogleBooksApiClient
	from app.services.google_books_repository import SQLiteGoogleBooksRepository
	from app.services.google_books_search import GoogleBooksSearchService


@lru_cache(maxsize=1)
def _build_chat_service() -> "ChatService":
	from app.core.config import get_settings
	from app.services.book_repository import BookRepository
	from app.services.chat_service import ChatService
	from app.services.chroma_store import ChromaVectorStore
	from app.services.input_filter import InputFilter
	from app.services.input_safety_validator import InputSafetyValidator
	from app.services.intent_classifier import IntentClassifier
	from app.services.llm_client import OpenAIClient
	from app.services.retriever import Retriever
	from app.services.summary_tool import SummaryTool
	from app.services.tool_call_executor import ToolCallExecutor

	settings = get_settings()
	book_repository = BookRepository(settings.book_data_path)
	llm_client = OpenAIClient(
		api_key=settings.openai_api_key.get_secret_value(),
		chat_model=settings.openai_chat_model,
		embedding_model=settings.openai_embedding_model,
	)
	validation_client = OpenAIClient(
		api_key=settings.openai_api_key.get_secret_value(),
		chat_model=settings.openai_validation_model,
		embedding_model=settings.openai_embedding_model,
	)
	vector_store = ChromaVectorStore(
		persist_directory=settings.chroma_persist_directory,
		collection_name=settings.chroma_collection_name,
	)
	return ChatService(
		input_filter=InputFilter(settings.filter_config_path, settings.max_question_length),
		retriever=Retriever(llm_client, vector_store, settings.top_k_results),
		llm_client=llm_client,
		tool_executor=ToolCallExecutor(SummaryTool(book_repository).get_summary_by_title),
		intent_classifier=IntentClassifier(llm_client),
		input_safety_validator=InputSafetyValidator(validation_client),
	)


class _LazyChatService:
	"""Defers API-key and infrastructure loading until a valid chat request arrives."""

	def recommend(self, request: "ChatRequest") -> "ChatResponse":
		return _build_chat_service().recommend(request)


@lru_cache(maxsize=1)
def get_chat_service() -> "ChatService":
	return cast("ChatService", _LazyChatService())


@lru_cache(maxsize=1)
def get_google_books_client() -> "GoogleBooksApiClient":
	from app.core.config import get_settings
	from app.services.google_books_client import GoogleBooksApiClient

	settings = get_settings()
	api_key = (
		settings.google_books_api_key.get_secret_value()
		if settings.google_books_api_key is not None
		else None
	)
	return GoogleBooksApiClient(
		base_url=settings.google_books_base_url,
		timeout_seconds=settings.google_books_timeout_seconds,
		max_results=settings.google_books_max_results,
		api_key=api_key,
	)


@lru_cache(maxsize=1)
def get_google_books_repository() -> "SQLiteGoogleBooksRepository":
	from app.core.config import get_settings
	from app.services.google_books_repository import SQLiteGoogleBooksRepository

	return SQLiteGoogleBooksRepository(get_settings().google_books_cache_path)


@lru_cache(maxsize=1)
def _build_google_books_search_service() -> "GoogleBooksSearchService":
	from app.core.config import get_settings
	from app.services.chroma_store import ChromaVectorStore
	from app.services.google_books_indexer import GoogleBooksIndexer
	from app.services.google_books_search import GoogleBooksSearchService
	from app.services.llm_client import OpenAIClient

	settings = get_settings()
	llm_client = OpenAIClient(
		api_key=settings.openai_api_key.get_secret_value(),
		chat_model=settings.openai_chat_model,
		embedding_model=settings.openai_embedding_model,
	)
	return GoogleBooksSearchService(
		client=get_google_books_client(),
		repository=get_google_books_repository(),
		indexer=GoogleBooksIndexer(
			llm_client,
			ChromaVectorStore(
				persist_directory=settings.chroma_persist_directory,
				collection_name=settings.google_books_collection_name,
			),
		),
	)


class _LazyGoogleBooksSearchService:
	"""Defers API-key and infrastructure loading until a valid search arrives."""

	def search(self, query: str, limit: int) -> tuple["GoogleBook", ...]:
		return _build_google_books_search_service().search(query, limit)


@lru_cache(maxsize=1)
def get_google_books_search_service() -> "GoogleBooksSearchService":
	return cast("GoogleBooksSearchService", _LazyGoogleBooksSearchService())