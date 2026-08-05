import json
from pathlib import Path

import pytest
from app.core.exceptions import BookDataError, BookNotFoundError
from app.services.book_repository import BookRepository

PRODUCTION_DATA_PATH = Path(__file__).parents[1] / "data" / "book_summaries.json"


def write_books(path, books: object) -> None:
	path.write_text(json.dumps(books), encoding="utf-8")


def test_repository_loads_books_and_finds_title_case_insensitively(tmp_path) -> None:
	data_path = tmp_path / "books.json"
	write_books(
		data_path,
		[
			{
				"title": "Dune",
				"author": "Frank Herbert",
				"summary": "A complete summary.",
			}
		],
	)
	repository = BookRepository(data_path)

	book = repository.get_by_title("  dune ")

	assert book.author == "Frank Herbert"
	assert repository.get_summary_by_title("DUNE") == "A complete summary."


def test_repository_loads_production_book_catalogue() -> None:
	repository = BookRepository(PRODUCTION_DATA_PATH)
	books = repository.list_books()

	assert len(books) == 12
	assert {book.title for book in books} == {
		"Frankenstein",
		"Jane Eyre",
		"Little Women",
		"Moby-Dick",
		"Pride and Prejudice",
		"The Adventures of Sherlock Holmes",
		"The Count of Monte Cristo",
		"The Picture of Dorian Gray",
		"The Secret Garden",
		"The Time Machine",
		"Twenty Thousand Leagues Under the Seas",
		"The Wonderful Wizard of Oz",
	}
	assert repository.get_summary_by_title("frankenstein").startswith("Victor Frankenstein creates")


def test_repository_rejects_invalid_json_shape(tmp_path) -> None:
	data_path = tmp_path / "books.json"
	write_books(data_path, {"books": []})

	with pytest.raises(BookDataError, match="JSON array"):
		BookRepository(data_path).list_books()


def test_repository_rejects_malformed_book_record(tmp_path) -> None:
	data_path = tmp_path / "books.json"
	write_books(data_path, [{"title": "Dune", "author": "Frank Herbert"}])

	with pytest.raises(BookDataError, match="Invalid book record at index 0"):
		BookRepository(data_path).list_books()


def test_repository_rejects_invalid_json(tmp_path) -> None:
	data_path = tmp_path / "books.json"
	data_path.write_text("not valid json", encoding="utf-8")

	with pytest.raises(BookDataError, match="Unable to load book data"):
		BookRepository(data_path).list_books()


def test_repository_rejects_duplicate_titles(tmp_path) -> None:
	data_path = tmp_path / "books.json"
	book = {"title": "Dune", "author": "Frank Herbert", "summary": "Summary."}
	write_books(data_path, [book, {**book, "title": "dUnE"}])

	with pytest.raises(BookDataError, match="Duplicate book title"):
		BookRepository(data_path).list_books()


def test_repository_raises_for_missing_title(tmp_path) -> None:
	data_path = tmp_path / "books.json"
	write_books(data_path, [])

	with pytest.raises(BookNotFoundError):
		BookRepository(data_path).get_by_title("Unknown")