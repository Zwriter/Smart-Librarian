from app.core.exceptions import LLMClientError
from app.domain.google_book import GoogleBook
from app.services.google_books.google_books_search import GoogleBooksSearchService


class FakeClient:
	def __init__(self, books: tuple[GoogleBook, ...]) -> None:
		self.books = books
		self.calls: list[tuple[str, int]] = []

	def search_volumes(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		self.calls.append((query, limit))
		return self.books


class FakeRepository:
	def __init__(self, cached: tuple[GoogleBook, ...] | None = None) -> None:
		self.cached = cached
		self.saved: tuple[str, tuple[GoogleBook, ...]] | None = None

	def get(self, _query: str) -> tuple[GoogleBook, ...] | None:
		return self.cached

	def save(self, query: str, books: tuple[GoogleBook, ...]) -> None:
		self.saved = (query, books)


class FailingIndexer:
	def index(self, books: tuple[GoogleBook, ...]) -> None:
		raise LLMClientError("embedding unavailable")


class RecordingIndexer:
	def __init__(self) -> None:
		self.books: list[tuple[GoogleBook, ...]] = []

	def index(self, books: tuple[GoogleBook, ...]) -> None:
		self.books.append(books)


def make_book(volume_id: str) -> GoogleBook:
	return GoogleBook(volume_id=volume_id, title="Dune")


def test_search_returns_cached_results_without_calling_provider() -> None:
	client = FakeClient((make_book("provider"),))
	repository = FakeRepository((make_book("cached"),))

	result = GoogleBooksSearchService(client, repository).search("Dune", 10)

	assert result[0].volume_id == "cached"
	assert client.calls == []


def test_search_repairs_missing_index_for_cached_results() -> None:
	client = FakeClient(())
	repository = FakeRepository((make_book("cached"),))
	indexer = RecordingIndexer()

	result = GoogleBooksSearchService(client, repository, indexer).search("Dune", 10)

	assert result == repository.cached
	assert indexer.books == [repository.cached]


def test_search_calls_provider_and_saves_cache_on_miss() -> None:
	client = FakeClient((make_book("provider"),))
	repository = FakeRepository()

	result = GoogleBooksSearchService(client, repository).search("Dune", 5)

	assert result == client.books
	assert client.calls == [("Dune", 5)]
	assert repository.saved == ("Dune", client.books)


def test_search_returns_provider_results_when_optional_indexing_fails() -> None:
	client = FakeClient((make_book("provider"),))
	repository = FakeRepository()

	result = GoogleBooksSearchService(client, repository, FailingIndexer()).search("Dune", 5)

	assert result == client.books
	assert repository.saved == ("Dune", client.books)


def test_exact_title_search_refreshes_cache_without_an_exact_match() -> None:
	client = FakeClient((make_book("provider"),))
	repository = FakeRepository((GoogleBook(volume_id="cached", title="Children of Dune"),))

	result = GoogleBooksSearchService(client, repository).search("intitle:Dune", 5)

	assert result == client.books
	assert client.calls == [("intitle:Dune", 10)]


def test_exact_title_search_applies_requested_limit_to_provider_results() -> None:
	client = FakeClient(
		(
			make_book("provider-1"),
			make_book("provider-2"),
		)
	)

	result = GoogleBooksSearchService(client, FakeRepository()).search(
		"intitle:Dune", 1
	)

	assert result == (client.books[0],)


def test_exact_title_search_matches_accents_and_hyphens() -> None:
	client = FakeClient(
		(
			GoogleBook(
				volume_id="fat-frumos",
				title="Făt-Frumos din lacrimă",
				language="ro",
			),
		)
	)

	result = GoogleBooksSearchService(client, FakeRepository()).search(
		"intitle:Fat Frumos din lacrima", 3
	)

	assert result[0].title == "Făt-Frumos din lacrimă"