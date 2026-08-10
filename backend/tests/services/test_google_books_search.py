from app.domain.google_book import GoogleBook
from app.services.google_books_search import GoogleBooksSearchService


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


def make_book(volume_id: str) -> GoogleBook:
	return GoogleBook(volume_id=volume_id, title="Dune")


def test_search_returns_cached_results_without_calling_provider() -> None:
	client = FakeClient((make_book("provider"),))
	repository = FakeRepository((make_book("cached"),))

	result = GoogleBooksSearchService(client, repository).search("Dune", 10)

	assert result[0].volume_id == "cached"
	assert client.calls == []


def test_search_calls_provider_and_saves_cache_on_miss() -> None:
	client = FakeClient((make_book("provider"),))
	repository = FakeRepository()

	result = GoogleBooksSearchService(client, repository).search("Dune", 5)

	assert result == client.books
	assert client.calls == [("Dune", 5)]
	assert repository.saved == ("Dune", client.books)