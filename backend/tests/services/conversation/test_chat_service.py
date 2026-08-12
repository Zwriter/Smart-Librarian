import pytest
from app.core.exceptions import BookNotFoundError, ChatServiceError, GoogleBooksError
from app.domain.book import Book
from app.domain.chat_request import ChatRequest
from app.domain.conversation_intent import ConversationIntent
from app.domain.conversation_message import ConversationMessage
from app.domain.google_book import GoogleBook
from app.domain.input_safety import InputSafetyResult
from app.domain.retrieved_book import RetrievedBook
from app.services.conversation.chat_service import ChatService
from app.services.llm.llm_client import ChatCompletionResult, ToolCall


class FakeInputFilter:
	def validate(self, question: str) -> str:
		return "normalized question"


class FakeRetriever:
	def retrieve(self, question: str) -> tuple[()]:
		return ()


class LocalDuneRetriever:
	def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
		return (
			RetrievedBook(
				book=Book(title="Dune", author="Frank Herbert", summary="A desert epic."),
				document_id="local-dune",
				relevance_score=1.0,
			),
		)


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


class FakeIntentClassifier:
	def __init__(self, intent: str, book_title: str | None = None) -> None:
		self.intent = intent
		self.book_title = book_title

	def classify(self, question, history=()):
		return ConversationIntent(
			intent=self.intent,
			requires_retrieval=self.intent in {"search", "recommendation", "book_summary"},
			requires_summary_tool=self.intent == "book_summary",
			book_title=self.book_title,
		)


class FakeInputSafetyValidator:
	def __init__(self, result: InputSafetyResult) -> None:
		self.result = result

	def validate(self, question, history=()):
		return self.result


class FakeGoogleBooksSearch:
	def __init__(self, books: tuple[GoogleBook, ...]) -> None:
		self.books = books
		self.queries: list[tuple[str, int]] = []

	def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		self.queries.append((query, limit))
		return self.books


def test_chat_service_uses_google_books_when_local_catalogue_is_empty() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="volume-1",
				title="Dune",
				authors=("Frank Herbert",),
				description="Politics and ecology collide on a desert world.",
			),
		)
	)

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			context = next(
				message["content"]
				for message in messages
				if message["content"].startswith("Retrieved catalogue context:")
			)
			assert "Source: Google Books (external metadata)" in context
			assert tools == ()
			return ChatCompletionResult(
				content='{"title":"Dune","author":"Frank Herbert","rationale":"A strong match."}'
			)

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Find Dune"))

	assert google_books.queries == [("normalized question", 3)]
	assert response.recommendation is not None
	assert response.summary == "Politics and ecology collide on a desert world."


def test_chat_service_does_not_use_google_books_when_local_catalogue_has_results() -> None:
	class FailingGoogleBooksSearch:
		def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
			raise AssertionError("Google Books should not run for local results")

	class LocalRetriever:
		def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
			return (
				RetrievedBook(
					book=Book(title="Dune", author="Frank Herbert", summary="A desert epic."),
					document_id="local-dune",
					relevance_score=1.0,
				),
			)

	service = ChatService(
		FakeInputFilter(),
		LocalRetriever(),  # type: ignore[arg-type]
		FakeLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		google_books_search=FailingGoogleBooksSearch(),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Find Dune"))

	assert response.recommendation is not None


def test_chat_service_uses_google_books_for_unmatched_specific_book_question() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="little-prince",
				title="The Little Prince",
				authors=("Antoine de Saint-Exupery",),
				description="A poetic tale about friendship, love, and responsibility.",
				published_date="1943",
				publisher="Reynal & Hitchcock",
			),
		)
	)

	class UnrelatedLocalRetriever:
		def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
			return (
				RetrievedBook(
					book=Book(title="Dune", author="Frank Herbert", summary="A desert epic."),
					document_id="local-dune",
					relevance_score=1.0,
				),
			)

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content=(
					'{"title":"The Little Prince",'
					'"author":"Antoine de Saint-Exupery",'
					'"rationale":"A thoughtful story about human connection."}'
				)
			)

	service = ChatService(
		FakeInputFilter(),
		UnrelatedLocalRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("search", "The Little Prince"),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Tell me something about The Little Prince"))

	assert google_books.queries == [("intitle:The Little Prince", 3)]
	assert response.recommendation is not None
	assert response.recommendation.title == "The Little Prince"
	assert response.recommendation.published_date == "1943"
	assert response.recommendation.publisher == "Reynal & Hitchcock"
	assert response.summary == "A poetic tale about friendship, love, and responsibility."


def test_chat_service_uses_google_books_for_a_bare_unmatched_title() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="little-prince",
				title="The Little Prince",
				authors=("Antoine de Saint-Exupery",),
				description="A poetic tale about friendship, love, and responsibility.",
			),
		)
	)

	class UnrelatedLocalRetriever:
		def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
			return (
				RetrievedBook(
					book=Book(title="Dune", author="Frank Herbert", summary="A desert epic."),
					document_id="local-dune",
					relevance_score=1.0,
				),
			)

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content=(
					'{"title":"The Little Prince",'
					'"author":"Antoine de Saint-Exupery",'
					'"rationale":"A thoughtful story about human connection."}'
				)
			)

	service = ChatService(
		FakeInputFilter(),
		UnrelatedLocalRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("search", "The Little Prince"),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="The Little Prince"))

	assert google_books.queries == [("intitle:The Little Prince", 3)]
	assert response.recommendation is not None


def test_chat_service_falls_back_to_google_books_when_title_resolution_misses() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="dune",
				title="Dune",
				authors=("Frank Herbert",),
				description="A desert epic.",
			),
		)
	)

	class MissingBookSearch:
		def find_by_title(self, title: str) -> Book:
			raise BookNotFoundError("not found")

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content='{"title":"Dune","author":"Frank Herbert","rationale":"A desert epic."}'
			)

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("book_summary", "Dune"),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
		book_search=MissingBookSearch(),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question='Tell me more about the book "Dune"'))

	assert google_books.queries == [("intitle:Dune", 3)]
	assert response.recommendation is not None


def test_chat_service_searches_google_books_for_unquoted_book_summary_title() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="dune",
				title="Dune",
				authors=("Frank Herbert",),
				description="A desert epic.",
			),
		)
	)

	class BookSummaryIntentClassifier:
		def classify(self, question, history=()):
			return ConversationIntent(
				intent="book_summary",
				requires_retrieval=False,
				requires_summary_tool=True,
				book_title="Dune",
			)

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content='{"title":"Dune","author":"Frank Herbert","rationale":"A desert epic."}'
			)

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		BookSummaryIntentClassifier(),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
		book_search=None,
	)

	response = service.recommend(ChatRequest(question="Tell me more about Dune"))

	assert google_books.queries == [("intitle:Dune", 3)]
	assert response.recommendation is not None
 


def test_chat_service_builds_external_recommendation_when_model_returns_message() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="dune",
				title="Dune",
				authors=("Frank Herbert",),
				description="A desert epic.",
			),
		)
	)

	class ExternalMessageLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(content='{"message":"I do not know that book."}')

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		ExternalMessageLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("book_summary", "Dune"),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Tell me about Dune"))

	assert response.recommendation is not None
	assert response.recommendation.title == "Dune"
	assert response.summary == "A desert epic."


def test_chat_service_prefers_external_books_in_response_language() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(volume_id="english", title="Dune", language="en"),
			GoogleBook(volume_id="romanian", title="Dune", language="ro"),
		)
	)

	class RomanianIntentClassifier:
		def classify(self, question, history=()):
			return ConversationIntent(
				intent="search",
				requires_retrieval=False,
				requires_summary_tool=False,
				book_title="Dune",
				response_language="ro",
			)

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content='{"title":"Dune","author":"Frank Herbert","rationale":"O alegere buna."}'
			)

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		RomanianIntentClassifier(),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Spune-mi despre Dune"))

	assert response.recommendation is not None
	assert response.summary == "No description available from Google Books."
	assert google_books.books[1].volume_id == "romanian"


def test_chat_service_does_not_use_local_summary_tool_when_search_returns_no_book() -> None:
	class EmptyGoogleBooksSearch:
		def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
			return ()

	class SearchResponseLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content='{"message":"I could not find that book."}',
			)

	class UnrelatedLocalRetriever:
		def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
			return (
				RetrievedBook(
					book=Book(title="Dune", author="Frank Herbert", summary="A desert epic."),
					document_id="local-dune",
					relevance_score=1.0,
				),
			)

	service = ChatService(
		FakeInputFilter(),
		UnrelatedLocalRetriever(),  # type: ignore[arg-type]
		SearchResponseLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("search", "Unknown Book"),  # type: ignore[arg-type]
		google_books_search=EmptyGoogleBooksSearch(),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Tell me about Unknown Book"))

	assert response.message == "I could not find that book."


def test_chat_service_keeps_google_book_follow_up_out_of_local_summary_tool() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="little-prince",
				title="The Little Prince",
				authors=("Antoine de Saint-Exupery",),
				description="A poetic tale about friendship, love, and responsibility.",
			),
		)
	)

	class IndexedGoogleBookRetriever:
		def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
			return (
				RetrievedBook(
					book=Book(
						title="THE LITTLE PRINCE",
						author="Antoine de Saint-Exupery",
						summary="A poetic tale about friendship, love, and responsibility.",
						metadata={"source": "google_books", "volume_id": "little-prince"},
					),
					document_id="google-volume:little-prince",
					relevance_score=1.0,
				),
			)

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content=(
					'{"title":"The Little Prince",'
					'"author":"Antoine de Saint-Exupery",'
					'"rationale":"A thoughtful story about human connection."}'
				)
			)

	service = ChatService(
		FakeInputFilter(),
		IndexedGoogleBookRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("search", "The Little Prince"),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
	)

	response = service.recommend(
		ChatRequest(question="Yes! I want to know more about THE LITTLE PRINCE")
	)

	assert response.recommendation is not None
	assert response.summary == "A poetic tale about friendship, love, and responsibility."


def test_chat_service_keeps_indexed_google_book_external_for_summary_intent() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="little-prince",
				title="The Little Prince",
				authors=("Antoine de Saint-Exupery",),
				description="A poetic tale about friendship, love, and responsibility.",
			),
		)
	)

	class IndexedGoogleBookRetriever:
		def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
			return (
				RetrievedBook(
					book=Book(
						title="The Little Prince",
						author="Antoine de Saint-Exupery",
						summary="A poetic tale about friendship, love, and responsibility.",
						metadata={"source": "google_books", "volume_id": "little-prince"},
					),
					document_id="google-volume:little-prince",
					relevance_score=1.0,
				),
			)

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content=(
					'{"title":"The Little Prince",'
					'"author":"Antoine de Saint-Exupery",'
					'"rationale":"A thoughtful story about human connection."}'
				)
			)

	service = ChatService(
		FakeInputFilter(),
		IndexedGoogleBookRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("book_summary", "The Little Prince"),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Tell me more about The Little Prince"))

	assert google_books.queries == [("intitle:The Little Prince", 3)]
	assert response.recommendation is not None
	assert response.summary == "A poetic tale about friendship, love, and responsibility."


def test_chat_service_queries_external_follow_up_by_classified_title() -> None:
	google_books = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="little-prince",
				title="The Little Prince",
				authors=("Antoine de Saint-Exupery",),
				description="A poetic tale about friendship, love, and responsibility.",
			),
		)
	)

	class ExternalBookSearch:
		def find_by_title(self, title: str) -> Book:
			return Book(
				title=title,
				author="Antoine de Saint-Exupery",
				summary="A poetic tale about friendship, love, and responsibility.",
				metadata={"source": "google_books", "volume_id": "little-prince"},
			)

	class ExternalRecommendationLLM:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content=(
					'{"title":"The Little Prince",'
					'"author":"Antoine de Saint-Exupery",'
					'"rationale":"A thoughtful story about human connection."}'
				)
			)

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		ExternalRecommendationLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("search", "The Little Prince"),  # type: ignore[arg-type]
		google_books_search=google_books,  # type: ignore[arg-type]
		book_search=ExternalBookSearch(),  # type: ignore[arg-type]
	)

	response = service.recommend(
		ChatRequest(question="Tell me more about The Little Prince")
	)

	assert google_books.queries == [("intitle:The Little Prince", 3)]
	assert response.recommendation is not None
	assert response.summary == "A poetic tale about friendship, love, and responsibility."


def test_chat_service_returns_message_when_external_title_lookup_fails() -> None:
	class UnavailableExternalBookSearch:
		def find_by_title(self, title: str) -> Book:
			raise GoogleBooksError("Google Books search failed")

	class FailingLLM:
		def create_chat_completion(self, messages, tools=()):
			raise AssertionError("LLM should not run after a failed title lookup")

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		FailingLLM(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("search", "The Little Prince"),  # type: ignore[arg-type]
		book_search=UnavailableExternalBookSearch(),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Tell me more about The Little Prince"))

	assert response.message == "I couldn't look up that book right now. Please try again shortly."


def test_chat_service_orchestrates_recommendation_and_summary() -> None:
	service = ChatService(
		FakeInputFilter(),
		LocalDuneRetriever(),  # type: ignore[arg-type]
		FakeLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("book_summary", "Dune"),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Find Dune"))

	assert response.recommendation.title == "Dune"
	assert response.recommendation.author == "Frank Herbert"
	assert response.summary == "Complete Dune summary."


def test_chat_service_compacts_long_book_summaries_to_forty_words() -> None:
	long_summary = " ".join(f"word{index}" for index in range(1, 46))

	class LongSummaryToolExecutor:
		def execute(self, tool_call: ToolCall) -> str:
			return long_summary

	service = ChatService(
		FakeInputFilter(),
		LocalDuneRetriever(),  # type: ignore[arg-type]
		FakeLLMClient(),  # type: ignore[arg-type]
		LongSummaryToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("book_summary", "Dune"),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Tell me more about Dune"))

	assert response.summary == " ".join(f"word{index}" for index in range(1, 41))
	assert len(response.summary.split()) == 40


def test_chat_service_keeps_short_book_summaries_unchanged() -> None:
	short_summary = "A classic horror story about creation and consequences."

	class ShortSummaryToolExecutor:
		def execute(self, tool_call: ToolCall) -> str:
			return short_summary

	service = ChatService(
		FakeInputFilter(),
		LocalDuneRetriever(),  # type: ignore[arg-type]
		FakeLLMClient(),  # type: ignore[arg-type]
		ShortSummaryToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("book_summary", "Dune"),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Tell me more about Dune"))

	assert response.summary == short_summary


def test_chat_service_returns_message_without_recommending_for_casual_questions() -> None:
	class ConversationalLLMClient:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content='{"message":"Hello. What kind of book are you looking for?"}',
			)

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		ConversationalLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("clarification"),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="What is this?"))

	assert response.recommendation is None
	assert response.summary is None
	assert response.message == "Hello. What kind of book are you looking for?"


def test_chat_service_greeting_explains_librarian_capabilities() -> None:
	class FailingRetriever:
		def retrieve(self, question: str):
			raise AssertionError("greetings should not reach retrieval")

	service = ChatService(
		FakeInputFilter(),
		FailingRetriever(),  # type: ignore[arg-type]
		FakeLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("greeting"),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="Hello"))

	assert response.message is not None
	assert "recommend books" in response.message
	assert "summarize books" in response.message


def test_chat_service_uses_model_intent_for_conversation() -> None:
	class FailingRetriever:
		def retrieve(self, question: str):
			raise AssertionError("conversation should not reach retrieval")

	service = ChatService(
		FakeInputFilter(),
		FailingRetriever(),  # type: ignore[arg-type]
		FakeLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("capabilities"),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="wht cn u do?"))

	assert response.message == ChatService.CAPABILITIES_MESSAGE


def test_chat_service_rejects_obscene_content_before_intent_classification() -> None:
	class FailingIntentClassifier:
		def classify(self, question, history=()):
			raise AssertionError("unsafe input should not reach intent classification")

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		FakeLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FailingIntentClassifier(),  # type: ignore[arg-type]
		FakeInputSafetyValidator(
			InputSafetyResult(
				allowed=False,
				category="obscene",
				reason="Obscene content.",
			)
		),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="obscene input"))

	assert response.message == ChatService.SAFETY_REJECTION_MESSAGE


@pytest.mark.parametrize("question", ["Heyy", "What can you do?"])
def test_chat_service_handles_conversation_without_book_or_llm_calls(question: str) -> None:
	class FailingDependency:
		def __getattr__(self, name: str):
			raise AssertionError(f"conversation should not call {name}")

	service = ChatService(
		FakeInputFilter(),
		FailingDependency(),  # type: ignore[arg-type]
		FailingDependency(),  # type: ignore[arg-type]
		FailingDependency(),  # type: ignore[arg-type]
		FakeIntentClassifier("greeting" if question == "Heyy" else "capabilities"),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question=question))

	assert response.message == ChatService.CAPABILITIES_MESSAGE


def test_chat_service_returns_three_options_for_ambiguous_requests() -> None:
	class AmbiguousLLMClient:
		def create_chat_completion(self, messages, tools=()):
			assert tools == ()
			return ChatCompletionResult(
				content=(
					'{"recommendations":['
					'{"title":"Dune","author":"Frank Herbert",'
					'"summary":"Politics, ecology, and prophecy on desert worlds."},'
					'{"title":"Foundation","author":"Isaac Asimov",'
					'"summary":"A mathematician predicts civilization collapse."},'
					'{"title":"Solaris","author":"Stanislaw Lem",'
					'"summary":"A mysterious planet challenges human understanding."}'
					'],"message":"Would you like to know more about one specific book?"}'
				)
			)

	service = ChatService(
		FakeInputFilter(),
		FakeRetriever(),  # type: ignore[arg-type]
		AmbiguousLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("recommendation"),  # type: ignore[arg-type]
	)

	response = service.recommend(ChatRequest(question="I want something good"))

	assert response.recommendations is not None
	assert len(response.recommendations) == 3
	assert response.message == "Would you like to know more about one specific book?"


def test_chat_service_prefers_fresh_books_after_a_previous_recommendation() -> None:
	class DiverseRetriever:
		def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
			return tuple(
				RetrievedBook(
					book=Book(title=title, author="Author", summary="Summary."),
					document_id=title.casefold(),
					relevance_score=1.0,
				)
				for title in ("Dune", "Foundation", "Solaris", "Frankenstein")
			)

	class AmbiguousLLMClient:
		def create_chat_completion(self, messages, tools=()):
			context = next(
				message["content"]
				for message in messages
				if message["content"].startswith("Retrieved catalogue context:")
			)
			assert "Title: Dune" not in context
			assert tools == ()
			return ChatCompletionResult(
				content=(
					'{"recommendations":['
					'{"title":"Foundation","author":"Author",'
					'"summary":"A mathematician predicts civilization collapse."},'
					'{"title":"Solaris","author":"Author",'
					'"summary":"A mysterious planet challenges human understanding."},'
					'{"title":"Frankenstein","author":"Author",'
					'"summary":"Creation, ambition, and consequence shape this horror classic."}'
					'],"message":"Would you like to know more about one specific book?"}'
				)
			)

	service = ChatService(
		FakeInputFilter(),
		DiverseRetriever(),  # type: ignore[arg-type]
		AmbiguousLLMClient(),  # type: ignore[arg-type]
		FakeToolExecutor(),  # type: ignore[arg-type]
		FakeIntentClassifier("recommendation"),  # type: ignore[arg-type]
	)

	response = service.recommend(
		ChatRequest(
			question="I want something adventurous",
			history=[
				ConversationMessage(
					role="assistant",
					content="Dune: An epic story of politics and survival.",
				)
			],
		)
	)

	assert response.recommendations is not None
	assert {option.title for option in response.recommendations} == {
		"Foundation",
		"Solaris",
		"Frankenstein",
	}


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


def test_chat_service_does_not_recommend_unknown_summary_title() -> None:
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

	assert response.recommendation is None
	assert response.summary is None
	assert response.message == "I don't know that book from the local catalogue."