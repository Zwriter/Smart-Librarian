import httpx
import pytest
from app.core.exceptions import GoogleBooksError
from app.services.google_books_client import GoogleBooksApiClient


def test_search_volumes_maps_google_payload() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		assert request.url.params["q"] == "Dune"
		assert request.url.params["maxResults"] == "2"
		return httpx.Response(
			200,
			json={
				"items": [
					{
						"id": "volume-1",
						"volumeInfo": {
							"title": "Dune",
							"authors": ["Frank Herbert"],
							"description": "A desert planet.",
							"industryIdentifiers": [
								{"type": "ISBN_13", "identifier": "9780441013593"}
							],
						}
					}
				]
			},
		)

	client = GoogleBooksApiClient(
		base_url="https://books.test/v1",
		client=httpx.Client(transport=httpx.MockTransport(handler)),
	)

	books = client.search_volumes(" Dune ", 2)

	assert books[0].volume_id == "volume-1"
	assert books[0].authors == ("Frank Herbert",)
	assert books[0].isbn_13 == "9780441013593"


def test_search_volumes_wraps_provider_errors() -> None:
	def handler(_request: httpx.Request) -> httpx.Response:
		return httpx.Response(503)

	client = GoogleBooksApiClient(client=httpx.Client(transport=httpx.MockTransport(handler)))

	with pytest.raises(GoogleBooksError, match="Google Books search failed"):
		client.search_volumes("Dune", 5)


def test_search_volumes_rejects_empty_query() -> None:
	client = GoogleBooksApiClient()

	with pytest.raises(ValueError, match="query must not be empty"):
		client.search_volumes(" ", 5)