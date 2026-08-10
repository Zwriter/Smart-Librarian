from pathlib import Path

import pytest
from app.core.exceptions import GoogleBooksError
from app.domain.google_book import GoogleBook
from app.services.google_books_repository import SQLiteGoogleBooksRepository


def make_book(volume_id: str = "volume-1") -> GoogleBook:
	return GoogleBook(
		volume_id=volume_id,
		title="Dune",
		authors=("Frank Herbert",),
		description="A desert planet.",
	)


def test_repository_returns_none_for_cache_miss(tmp_path: Path) -> None:
	repository = SQLiteGoogleBooksRepository(tmp_path / "cache.sqlite3")

	assert repository.get("Dune") is None


def test_repository_round_trips_books_and_normalizes_query(tmp_path: Path) -> None:
	repository = SQLiteGoogleBooksRepository(tmp_path / "cache.sqlite3")
	book = make_book()

	repository.save("  DUNE  ", [book])

	assert repository.get("dune") == (book,)


def test_repository_caches_empty_results(tmp_path: Path) -> None:
	repository = SQLiteGoogleBooksRepository(tmp_path / "cache.sqlite3")

	repository.save("unknown title", [])

	assert repository.get("unknown   title") == ()


def test_repository_replaces_existing_query_results(tmp_path: Path) -> None:
	repository = SQLiteGoogleBooksRepository(tmp_path / "cache.sqlite3")
	repository.save("Dune", [make_book()])

	repository.save("Dune", [make_book("volume-2")])

	assert repository.get("Dune")[0].volume_id == "volume-2"


@pytest.mark.parametrize("query", ["", "   "])
def test_repository_rejects_empty_query(tmp_path: Path, query: str) -> None:
	repository = SQLiteGoogleBooksRepository(tmp_path / "cache.sqlite3")

	with pytest.raises(ValueError, match="query must not be empty"):
		repository.get(query)

	with pytest.raises(ValueError, match="query must not be empty"):
		repository.save(query, [])


def test_repository_wraps_corrupt_cached_json(tmp_path: Path) -> None:
	database_path = tmp_path / "cache.sqlite3"
	repository = SQLiteGoogleBooksRepository(database_path)
	repository.save("Dune", [make_book()])
	with repository._connect() as connection:
		connection.execute(
			"UPDATE google_books_cache SET books_json = ? WHERE query_key = ?",
			("not-json", "dune"),
		)

	with pytest.raises(GoogleBooksError, match="Unable to read Google Books cache"):
		repository.get("Dune")