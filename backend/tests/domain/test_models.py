import pytest
from app.domain.book import Book
from app.domain.retrieved_book import RetrievedBook
from pydantic import ValidationError


def test_book_strips_text_and_defaults_metadata() -> None:
    book = Book(title="  Dune  ", author="  Frank Herbert ", summary="  A summary.  ")

    assert book.title == "Dune"
    assert book.author == "Frank Herbert"
    assert book.summary == "A summary."
    assert book.metadata == {}


def test_book_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Book(title="Dune", author="Frank Herbert", summary="A summary.", year=1965)


def test_retrieved_book_requires_non_negative_relevance_score() -> None:
    book = Book(title="Dune", author="Frank Herbert", summary="A summary.")

    with pytest.raises(ValidationError):
        RetrievedBook(book=book, document_id="dune", relevance_score=-1)