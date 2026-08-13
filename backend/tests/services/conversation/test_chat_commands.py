from app.domain.book import Book
from app.domain.chat_request import ChatRequest
from app.domain.google_book import GoogleBook
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

	def find_by_title(self, title: str) -> Book:
		return self.book


def test_parser_returns_typed_commands_and_ignores_normal_chat() -> None:
	parser = ChatCommandParser()

	assert parser.parse("/query Dune").book_title == "Dune"  # type: ignore[union-attr]
	assert parser.parse("/search space opera").query == "space opera"  # type: ignore[union-attr]
	assert parser.parse("/language Dune").kind == "language"  # type: ignore[union-attr]
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


def test_handler_returns_typed_metadata_values() -> None:
	handler = ChatCommandHandler(
		FakeRetriever(()),  # type: ignore[arg-type]
		FakeGoogleBooksSearch(()),  # type: ignore[arg-type]
		FakeBookSearch(make_book()),  # type: ignore[arg-type]
	)

	response = handler.execute(ChatCommandParser().parse("/year Dune"))  # type: ignore[arg-type]

	assert response.message == "Dune year: 1965"


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