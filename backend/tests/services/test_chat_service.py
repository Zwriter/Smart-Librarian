import pytest
from app.core.exceptions import BookNotFoundError, ChatServiceError
from app.domain.book import Book
from app.domain.chat_request import ChatRequest
from app.domain.retrieved_book import RetrievedBook
from app.services.chat_service import ChatService
from app.services.llm_client import ChatCompletionResult, ToolCall


class FakeInputFilter:
	def validate(self, question: str) -> str:
		return "normalized question"


class FakeRetriever:
	def retrieve(self, question: str) -> tuple[()]:
		return ()


class FakeLLMClient:
	def create_chat_completion(self, messages, tools=()):
		assert messages[-1] == {"role": "user", "content": "normalized question"}
		assert tools[0]["function"]["name"] == "get_summary_by_title"
		return ChatCompletionResult(
			content='{"title":"Dune","author":"Frank Herbert","rationale":"A strong match."}',
			tool_calls=(
				ToolCall(
					id="call-1",
					name="get_summary_by_title",
					arguments='{"title":"Dune"}',
				),
			),
		)


class FakeToolExecutor:
	def execute(self, tool_call: ToolCall) -> str:
		return "Complete Dune summary."


def test_chat_service_orchestrates_recommendation_and_summary() -> None:
	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		FakeLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Find a book"))

	assert response.recommendation.title == "Dune"
	assert response.recommendation.author == "Frank Herbert"
	assert response.summary == "Complete Dune summary."


def test_chat_service_rejects_invalid_recommendation() -> None:
	class InvalidLLMClient(FakeLLMClient):
		def create_chat_completion(self, messages, tools=()):
			return ChatCompletionResult(
				content="not-json",
				tool_calls=(
					ToolCall(
						id="call-1",
						name="get_summary_by_title",
						arguments='{"title":"Dune"}',
					),
				),
			)

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		InvalidLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
	)

	with pytest.raises(ChatServiceError, match="invalid JSON"):
		service.recommend(ChatRequest(question="Find a book"))


def test_chat_service_completes_recommendation_after_tool_only_response() -> None:
	class TwoStepLLMClient(FakeLLMClient):
		calls = 0

		def create_chat_completion(self, messages, tools=()):
			self.calls += 1
			if self.calls == 1:
				return ChatCompletionResult(
					content=None,
					tool_calls=(
						ToolCall(
							id="call-1",
							name="get_summary_by_title",
							arguments='{"title":"Dune"}',
						),
					),
				)
			assert tools == ()
			return ChatCompletionResult(
				content='{"title":"Dune","author":"Frank Herbert","rationale":"A strong match."}',
			)

	client = TwoStepLLMClient()
	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		client,  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Find a book"))

	assert response.recommendation.title == "Dune"
	assert client.calls == 2


def test_chat_service_corrects_unknown_summary_title() -> None:
	class RetrievedBookFakeRetriever:
		def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
			return (
				RetrievedBook(
					book=Book(title="Dune", author="Frank Herbert", summary="Summary."),
					document_id="dune",
					relevance_score=1.0,
				),
			)

	class UnknownTitleExecutor:
		calls = 0

		def execute(self, tool_call: ToolCall) -> str:
			self.calls += 1
			if self.calls == 1:
				raise BookNotFoundError("not found")
			return "Complete Dune summary."

	class CorrectingLLMClient(FakeLLMClient):
		calls = 0

		def create_chat_completion(self, messages, tools=()):
			self.calls += 1
			if self.calls == 1:
				return ChatCompletionResult(
					content=None,
					tool_calls=(
						ToolCall(
							id="call-1",
							name="get_summary_by_title",
							arguments='{"title":"Unknown"}',
						),
					),
				)
			return ChatCompletionResult(
				content='{"title":"Dune","author":"Frank Herbert","rationale":"A strong match."}',
				tool_calls=(
					ToolCall(
						id="call-2",
						name="get_summary_by_title",
						arguments='{"title":"Dune"}',
					),
				),
			)

	service = ChatService(
		FakeInputFilter(),
		RetrievedBookFakeRetriever(),  # type: ignore[arg-type]
		CorrectingLLMClient(),  # type: ignore[arg-type]
		UnknownTitleExecutor(),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Find a book"))

	assert response.recommendation.title == "Dune"