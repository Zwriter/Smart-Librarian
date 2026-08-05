from functools import lru_cache
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
	from app.domain.chat_request import ChatRequest
	from app.domain.chat_response import ChatResponse
	from app.services.chat_service import ChatService


@lru_cache(maxsize=1)
def _build_chat_service() -> "ChatService":
	from app.core.config import get_settings
	from app.services.book_repository import BookRepository
	from app.services.chat_service import ChatService
	from app.services.chroma_store import ChromaVectorStore
	from app.services.input_filter import InputFilter
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
	vector_store = ChromaVectorStore(
		persist_directory=settings.chroma_persist_directory,
		collection_name=settings.chroma_collection_name,
	)
	return ChatService(
		input_filter=InputFilter(settings.filter_config_path, settings.max_question_length),
		retriever=Retriever(llm_client, vector_store, settings.top_k_results),
		llm_client=llm_client,
		tool_executor=ToolCallExecutor(SummaryTool(book_repository).get_summary_by_title),
	)


class _LazyChatService:
	"""Defers API-key and infrastructure loading until a valid chat request arrives."""

	def recommend(self, request: "ChatRequest") -> "ChatResponse":
		return _build_chat_service().recommend(request)


@lru_cache(maxsize=1)
def get_chat_service() -> "ChatService":
	return cast("ChatService", _LazyChatService())