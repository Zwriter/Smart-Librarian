import pytest
from app.core.exceptions import BookNotFoundError
from app.domain.book import Book
from app.domain.google_book import GoogleBook
from app.services.catalogue.book_search_service import BookSearchService


class FakeBookRepository:
	def __init__(self, book: Book | None = None) -> None:
		self.book = book
		self.calls: list[str] = []

	def get_by_title(self, title: str) -> Book:
		self.calls.append(title)
		if self.book is None:
			raise BookNotFoundError("not found")
		return self.book


class FakeGoogleBooksSearch:
	def __init__(self, books: tuple[GoogleBook, ...]) -> None:
		self.books = books
		self.calls: list[tuple[str, int]] = []

	def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		self.calls.append((query, limit))
		return self.books


def test_book_search_returns_local_book_without_calling_api() -> None:
	local_book = Book(title="Dune", author="Frank Herbert", summary="A desert epic.")
	repository = FakeBookRepository(local_book)
	provider = FakeGoogleBooksSearch(())

	result = BookSearchService(repository, provider).find_by_title("Dune")  # type: ignore[arg-type]

	assert result == local_book
	assert provider.calls == []


def test_book_search_falls_back_to_api_and_normalizes_external_book() -> None:
	repository = FakeBookRepository()
	provider = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="little-prince",
				title="The Little Prince",
				authors=("Antoine de Saint-Exupery",),
				description="A poetic tale.",
			),
		)
	)

	result = BookSearchService(repository, provider).find_by_title("the little prince")  # type: ignore[arg-type]

	assert result.title == "The Little Prince"
	assert result.author == "Antoine de Saint-Exupery"
	assert result.summary == "A poetic tale."
	assert result.metadata == {"source": "google_books", "volume_id": "little-prince"}
	assert provider.calls == [("the little prince", 10)]


def test_book_search_raises_when_local_and_api_have_no_exact_title() -> None:
	service = BookSearchService(FakeBookRepository(), FakeGoogleBooksSearch(()))  # type: ignore[arg-type]

	with pytest.raises(BookNotFoundError):
		service.find_by_title("Unknown Book")


def test_book_search_accepts_quoted_plural_title_for_external_match() -> None:
	provider = FakeGoogleBooksSearch(
		(
			GoogleBook(
				volume_id="dune",
				title="Dune",
				authors=("Frank Herbert",),
				description="A desert epic.",
			),
		)
	)

	result = BookSearchService(FakeBookRepository(), provider).find_by_title('"Dunes"')  # type: ignore[arg-type]

	assert result.title == "Dune"