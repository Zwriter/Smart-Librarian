from app.api.dependencies import get_google_books_search_service
from app.core.exceptions import GoogleBooksError
from app.domain.google_book import GoogleBook
from app.main import create_app
from fastapi.testclient import TestClient


class FakeSearchService:
	def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		assert query == "Dune"
		assert limit == 2
		return (GoogleBook(volume_id="volume-1", title="Dune"),)


def test_books_search_route_returns_normalized_results() -> None:
	application = create_app()
	application.dependency_overrides[get_google_books_search_service] = lambda: FakeSearchService()

	response = TestClient(application).get("/books/search", params={"query": "Dune", "limit": 2})

	assert response.status_code == 200
	assert response.json()["total"] == 1
	assert response.json()["items"][0]["volume_id"] == "volume-1"


def test_books_search_route_validates_query() -> None:
	response = TestClient(create_app()).get("/books/search", params={"query": ""})

	assert response.status_code == 422


def test_books_search_route_validates_limit() -> None:
	response = TestClient(create_app()).get(
		"/books/search", params={"query": "Dune", "limit": 41}
	)

	assert response.status_code == 422


def test_books_search_route_hides_provider_failure() -> None:
	class FailingSearchService:
		def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
			raise GoogleBooksError("provider credentials leaked")

	application = create_app()
	application.dependency_overrides[get_google_books_search_service] = (
		lambda: FailingSearchService()
	)

	response = TestClient(application).get("/books/search", params={"query": "Dune"})

	assert response.status_code == 502
	assert response.json() == {
		"detail": "The recommendation service is temporarily unavailable."
	}
	assert "provider credentials leaked" not in response.text