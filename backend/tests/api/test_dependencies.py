import app.core.config
from app.api import dependencies
from app.core.config import Settings


def test_google_books_dependency_uses_configured_settings(monkeypatch) -> None:
	settings = Settings(
		_env_file=None,
		openai_api_key="openai-test-key",
		google_books_api_key="google-test-key",
		google_books_base_url="https://books.test/v1",
		google_books_timeout_seconds=3.5,
		google_books_max_results=7,
	)
	monkeypatch.setattr(app.core.config, "get_settings", lambda: settings)
	dependencies.get_google_books_client.cache_clear()

	client = dependencies.get_google_books_client()

	assert client._base_url == "https://books.test/v1"
	assert client._timeout_seconds == 3.5
	assert client._max_results == 7
	assert client._api_key == "google-test-key"
	dependencies.get_google_books_client.cache_clear()