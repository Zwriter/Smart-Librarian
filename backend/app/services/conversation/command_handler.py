from collections.abc import Sequence
from typing import Protocol

from app.core.exceptions import BookNotFoundError, GoogleBooksError
from app.domain.book import Book
from app.domain.chat_command import ChatCommand, MetadataCommand, QueryCommand, SearchCommand
from app.domain.chat_response import ChatResponse
from app.domain.google_book import GoogleBook
from app.domain.retrieved_book import RetrievedBook
from app.services.catalogue.book_search_service import BookSearchService
from app.services.retrieval.retriever import Retriever


class GoogleBooksSearch(Protocol):
	def search(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		...


class ChatCommandHandler:
	"""Executes read-only chat commands against catalogue services."""

	def __init__(
		self,
		retriever: Retriever,
		google_books_search: GoogleBooksSearch,
		book_search: BookSearchService,
		indexed_retriever: Retriever | None = None,
	) -> None:
		self._retriever = retriever
		self._indexed_retriever = indexed_retriever
		self._google_books_search = google_books_search
		self._book_search = book_search

	def execute(self, command: ChatCommand) -> ChatResponse:
		if isinstance(command, QueryCommand):
			return self._query(command)
		if isinstance(command, SearchCommand):
			return self._search(command)
		return self._metadata(command)

	def _query(self, command: QueryCommand) -> ChatResponse:
		books = self._retriever.retrieve(command.book_title)
		if self._indexed_retriever is not None:
			indexed_books = self._indexed_retriever.retrieve(command.book_title)
			books = (*indexed_books, *books)
		books = self._unique_results(books)
		if not books:
			return ChatResponse(
				message=f'No local catalogue entries found for "{command.book_title}".'
			)
		return ChatResponse(message=self._format_local_results(books))

	def _search(self, command: SearchCommand) -> ChatResponse:
		try:
			books = self._google_books_search.search(command.query, 10)
		except GoogleBooksError:
			return ChatResponse(
				message="I couldn't search Google Books right now. Please try again shortly."
			)
		if not books:
			return ChatResponse(message=f'No Google Books results found for "{command.query}".')
		return ChatResponse(message=self._format_external_results(books))

	def _metadata(self, command: MetadataCommand) -> ChatResponse:
		try:
			book = self._book_search.find_by_title(command.book_title)
		except BookNotFoundError:
			return ChatResponse(message=f'I couldn\'t find "{command.book_title}".')
		except GoogleBooksError:
			return ChatResponse(
				message="I couldn't look up that book right now. Please try again shortly."
			)

		value = self._metadata_value(book, command.kind)
		if value is None:
			return ChatResponse(
				message=f"I don't have {command.kind} information for \"{book.title}\"."
			)
		return ChatResponse(message=f"{book.title} {command.kind}: {value}")

	@staticmethod
	def _metadata_value(book: Book, kind: str) -> str | None:
		metadata = book.metadata
		if kind == "author":
			return book.author
		if kind == "year":
			return metadata.get("year") or metadata.get("published_date")
		return metadata.get("language")

	@staticmethod
	def _format_local_results(books: Sequence[RetrievedBook]) -> str:
		lines = ["Embedded catalogue results:"]
		lines.extend(f"- {book.book.title} by {book.book.author}" for book in books)
		return "\n".join(lines)

	@staticmethod
	def _unique_results(books: Sequence[RetrievedBook]) -> tuple[RetrievedBook, ...]:
		unique: dict[str, RetrievedBook] = {}
		for book in books:
			unique.setdefault(book.document_id, book)
		return tuple(unique.values())

	@staticmethod
	def _format_external_results(books: Sequence[GoogleBook]) -> str:
		lines = ["Google Books results:"]
		for book in books:
			author = ", ".join(book.authors) or "Unknown author"
			publication = f" ({book.published_date})" if book.published_date else ""
			lines.append(f"- {book.title} by {author}{publication}")
		return "\n".join(lines)