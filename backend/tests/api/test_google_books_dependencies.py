from pathlib import Path

import app.core.config
from app.api import dependencies
from app.core.config import Settings


def test_google_books_repository_dependency_uses_configured_path(
	monkeypatch, tmp_path: Path
) -> None:
	settings = Settings(
		_env_file=None,
		openai_api_key="openai-test-key",
		google_books_cache_path=tmp_path / "books.sqlite3",
	)
	monkeypatch.setattr(app.core.config, "get_settings", lambda: settings)
	dependencies.get_google_books_repository.cache_clear()

	repository = dependencies.get_google_books_repository()

	assert (tmp_path / "books.sqlite3").is_file()
	assert repository._database_path == tmp_path / "books.sqlite3"
	dependencies.get_google_books_repository.cache_clear()