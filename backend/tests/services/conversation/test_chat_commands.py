from app.core.exceptions import BookNotFoundError
from app.domain.book import Book
from app.domain.chat_request import ChatRequest
from app.domain.conversation_message import ConversationMessage
from app.domain.google_book import GoogleBook
from app.domain.input_safety import InputSafetyResult
from app.domain.retrieved_book import RetrievedBook
from app.services.conversation.chat_service import ChatService
from app.services.conversation.command_handler import ChatCommandHandler
from app.services.conversation.command_parser import ChatCommandParser


def make_book(title: str = "Dune") -> Book:
	return Book(
		title=title,
		author="Frank Herbert",
		summary="A desert epic.",
		metadata={"year": "1965", "language": "en"},
	)


class FakeRetriever:
	def __init__(self, books: tuple[RetrievedBook, ...]) -> None:
		self.books = books
		self.questions: list[str] = []

	def retrieve(self, question: str) -> tuple[RetrievedBook, ...]:
		self.questions.append(question)
		return self.books


class FakeIndexedRetriever(FakeRetriever):
	pass


class FakeGoogleBooksSearch:
	def __init__(self, books: tuple[GoogleBook, ...]) -> None:
		self.books = books
		self.queries: list[tuple[str, int]] = []

	def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		self.queries.append((query, limit))
		return self.books


class FakeBookSearch:
	def __init__(self, book: Book) -> None:
		self.book = book
		self.titles: list[str] = []

	def find_by_title(self, title: str, required_metadata: str | None = None) -> Book:
		self.titles.append(title)
		return self.book


def test_parser_returns_typed_commands_and_ignores_normal_chat() -> None:
	parser = ChatCommandParser()

	assert parser.parse("/query Dune").book_title == "Dune"  # type: ignore[union-attr]
	assert parser.parse("/search space opera").query == "space opera"  # type: ignore[union-attr]
	assert parser.parse("/language Dune").kind == "language"  # type: ignore[union-attr]
	assert parser.parse("/resume Dune").kind == "resume"  # type: ignore[union-attr]
	assert parser.parse("/description Dune").kind == "description"  # type: ignore[union-attr]
	assert parser.parse("/get Dune").kind == "get"  # type: ignore[union-attr]
	assert parser.parse("Recommend a quiet mystery") is None


def test_handler_queries_local_retrieval() -> None:
	book = make_book()
	retriever = FakeRetriever((RetrievedBook(book=book, document_id="dune", relevance_score=1.0),))
	handler = ChatCommandHandler(
		retriever,  # type: ignore[arg-type]
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		FakeBookSearch(book),  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/query Dune"))  # type: ignore[arg-type]

	assert response.message == "Embedded catalogue results:\n- Dune by Frank Herbert"
	assert retriever.questions == ["Dune"]


def test_handler_queries_embeddings_and_keeps_relevant_results() -> None:
	exact_book = make_book("Outlander")
	related_book = make_book("The Time Traveler's Wife")
	unrelated_book = make_book("The Little Prince")
	book_search = FakeBookSearch(make_book("Unused title lookup"))
	retriever = FakeRetriever(
		(
			RetrievedBook(book=exact_book, document_id="outlander", relevance_score=1.0),
			RetrievedBook(
				book=unrelated_book, document_id="little-prince", relevance_score=0.2
			),
			RetrievedBook(
				book=related_book, document_id="time-travelers-wife", relevance_score=0.8
			),
		)
	)
	handler = ChatCommandHandler(
		retriever,  # type: ignore[arg-type]
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		book_search,  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/query Outlander"))  # type: ignore[arg-type]

	assert response.message == (
		"Embedded catalogue results:\n"
		"- Outlander by Frank Herbert\n"
		"- The Time Traveler's Wife by Frank Herbert"
	)
	assert book_search.titles == []


def test_handler_keeps_semantic_results_when_exact_title_is_missing() -> None:
	class MissingBookSearch:
		def find_by_title(self, title: str, required_metadata: str | None = None) -> Book:
			raise BookNotFoundError(title)

	related_book = make_book("The Time Traveler's Wife")
	handler = ChatCommandHandler(
		FakeRetriever(
			(
				RetrievedBook(
					book=related_book,
					document_id="time-travelers-wife",
					relevance_score=0.8,
				),
			)
		),  # type: ignore[arg-type]
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		MissingBookSearch(),  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/query Unknown Romance"))  # type: ignore[arg-type]

	assert response.message == (
		"Embedded catalogue results:\n- The Time Traveler's Wife by Frank Herbert"
	)


def test_handler_returns_book_not_found_without_calling_google_books() -> None:
	google = FakeGoogleBooksSearch(())
	handler = ChatCommandHandler(
		FakeRetriever(()),  # type: ignore[arg-type]
		google,  # type: ignore[arg-type]
		FakeBookSearch(make_book()),  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/query Unknown"))  # type: ignore[arg-type]

	assert response.message == 'Book Not Found: "Unknown".'
	assert google.queries == []


def test_handler_queries_google_books_embeddings_when_available() -> None:
	book = make_book("The Little Prince")
	indexed_retriever = FakeIndexedRetriever(
		(
			RetrievedBook(
				book=book,
				document_id="google-volume:little-prince",
				relevance_score=1.0,
			),
		)
	)
	handler = ChatCommandHandler(
		FakeRetriever(()),  # type: ignore[arg-type]
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		FakeBookSearch(book),  # type: ignore[arg-type]
		indexed_retriever=indexed_retriever,  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/query The Little Prince"))  # type: ignore[arg-type]

	assert response.message == "Embedded catalogue results:\n- The Little Prince by Frank Herbert"


def test_handler_searches_google_books() -> None:
	google = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="dune",
				title="Dune",
				authors=("Frank Herbert",),
				published_date="1965",
			),
		)
	)
	handler = ChatCommandHandler(
		FakeRetriever(()),  # type: ignore[arg-type]
		google,  # type: ignore[arg-type]
		FakeBookSearch(make_book()),  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/search Dune"))  # type: ignore[arg-type]

	assert response.message == "Google Books results:\n- Dune by Frank Herbert (1965)"
	assert google.queries == [("Dune", 10)]


def test_handler_search_returns_embedded_results_before_google_books() -> None:
	google = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="external-dune",
				title="Dune",
				authors=("Frank Herbert",),
			),
		)
	)
	handler = ChatCommandHandler(
		FakeRetriever(
			(
				RetrievedBook(
					book=make_book(), document_id="dune", relevance_score=0.9
				),
			)
		),  # type: ignore[arg-type]
		google,  # type: ignore[arg-type]
		FakeBookSearch(make_book()),  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/search Dune"))  # type: ignore[arg-type]

	assert response.message == "Embedded catalogue results:\n- Dune by Frank Herbert"
	assert google.queries == []


def test_handler_returns_typed_metadata_values() -> None:
	handler = ChatCommandHandler(
		FakeRetriever(()),  # type: ignore[arg-type]
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		FakeBookSearch(make_book()),  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/year Dune"))  # type: ignore[arg-type]

	assert response.message == "Dune year: 1965"


def test_handler_returns_resume_description_and_book() -> None:
	book = make_book()
	book.description = "A fuller description."
	handler = ChatCommandHandler(
		FakeRetriever(()),
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		FakeBookSearch(book),  # type: ignore[arg-type]
	)

	resume = handler.execute(ChatCommandParser().parse("/resume Dune"))  # type: ignore[arg-type]
	description = handler.execute(ChatCommandParser().parse("/description Dune"))  # type: ignore[arg-type]
	full_book = handler.execute(ChatCommandParser().parse("/get Dune"))  # type: ignore[arg-type]

	assert resume.message == "Dune resume: A desert epic."
	assert description.message == "Dune description: A fuller description."
	assert full_book.message == (
		"Title: Dune\nAuthor: Frank Herbert\nResume: A desert epic.\n"
		"Description: A fuller description."
	)


def test_handler_truncates_description_after_forty_words_without_changing_resume() -> None:
	words = tuple(f"word{index}" for index in range(1, 42))
	book = make_book()
	book.description = " ".join(words)
	handler = ChatCommandHandler(
		FakeRetriever(()),
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		FakeBookSearch(book),  # type: ignore[arg-type]
	)

	resume = handler.execute(ChatCommandParser().parse("/resume Dune"))  # type: ignore[arg-type]
	description = handler.execute(ChatCommandParser().parse("/description Dune"))  # type: ignore[arg-type]

	assert resume.message == "Dune resume: A desert epic."
	assert description.message == (
		"Dune description: " + " ".join(words[:40]) + "..."
	)


def test_handler_does_not_use_resume_as_description_fallback() -> None:
	book = make_book()
	book.description = None
	handler = ChatCommandHandler(
		FakeRetriever(()),
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		FakeBookSearch(book),  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/description Dune"))  # type: ignore[arg-type]

	assert response.message == 'I don\'t have description information for "Dune".'


def test_chat_service_executes_commands_before_intent_classification() -> None:
	class FailingClassifier:
		def classify(self, question, history=()):
			raise AssertionError("commands must bypass intent classification")

	book = make_book()
	service = ChatService(
		input_filter=type("Filter", (), {"validate": lambda _, question: question})(),  # type: ignore[arg-type]
		retriever=FakeRetriever(()),  # type: ignore[arg-type]
		llm_client=object(),  # type: ignore[arg-type]
		tool_executor=object(),  # type: ignore[arg-type]
		intent_classifier=FailingClassifier(),  # type: ignore[arg-type]
		command_parser=ChatCommandParser(),
		command_handler=ChatCommandHandler(
			FakeRetriever(()),  # type: ignore[arg-type]
			FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
			FakeBookSearch(book),  # type: ignore[arg-type]
		),
	)

	response = service.recommend(ChatRequest(question="/author Dune"))

	assert response.message == "Dune author: Frank Herbert"


def test_chat_commands_are_not_rejected_by_previous_history_safety_result() -> None:
	class HistorySensitiveSafety:
		def validate(self, question, history=()):
			return InputSafetyResult(
				allowed=not history,
				category="allowed" if not history else "profanity",
				reason=None,
			)

	book = make_book()
	service = ChatService(
		input_filter=type("Filter", (), {"validate": lambda _, question: question})(),  # type: ignore[arg-type]
		retriever=FakeRetriever(()),  # type: ignore[arg-type]
		llm_client=object(),  # type: ignore[arg-type]
		tool_executor=object(),  # type: ignore[arg-type]
		intent_classifier=None,
		input_safety_validator=HistorySensitiveSafety(),  # type: ignore[arg-type]
		command_parser=ChatCommandParser(),
		command_handler=ChatCommandHandler(
			FakeRetriever(()),  # type: ignore[arg-type]
			FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
			FakeBookSearch(book),  # type: ignore[arg-type]
		),
	)

	response = service.recommend(
		ChatRequest(
			question="/year Dune",
			history=[ConversationMessage(role="user", content="unsafe prior text")],
		)
	)

	assert response.message == "Dune year: 1965"