import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from app.core.exceptions import GoogleBooksError
from app.domain.google_book import GoogleBook
from pydantic import ValidationError


class GoogleBooksRepository(Protocol):
	"""Persistence boundary for cached public Google Books results."""

	def get(self, query: str) -> tuple[GoogleBook, ...] | None:
		...

	def save(self, query: str, books: Sequence[GoogleBook]) -> None:
		...


class SQLiteGoogleBooksRepository:
	"""Stores validated Google Books search results in a local SQLite database."""

	def __init__(self, database_path: Path) -> None:
		self._database_path = database_path
		try:
			self._database_path.parent.mkdir(parents=True, exist_ok=True)
			with self._connect() as connection:
				connection.execute(
					"""
					CREATE TABLE IF NOT EXISTS google_books_cache (
						query_key TEXT PRIMARY KEY,
						books_json TEXT NOT NULL
					)
					"""
				)
		except sqlite3.Error as error:
			raise GoogleBooksError("Unable to initialize Google Books cache") from error

	def get(self, query: str) -> tuple[GoogleBook, ...] | None:
		query_key = self._normalize_query(query)
		try:
			with self._connect() as connection:
				row = connection.execute(
					"SELECT books_json FROM google_books_cache WHERE query_key = ?",
					(query_key,),
				).fetchone()
			if row is None:
				return None
			payload = json.loads(row[0])
			if not isinstance(payload, list):
				raise ValueError("cached books must be a JSON array")
			return tuple(GoogleBook.model_validate(item) for item in payload)
		except (
			sqlite3.Error,
			OSError,
			json.JSONDecodeError,
			TypeError,
			ValueError,
			ValidationError,
		) as error:
			raise GoogleBooksError("Unable to read Google Books cache") from error

	def save(self, query: str, books: Sequence[GoogleBook]) -> None:
		query_key = self._normalize_query(query)
		payload = json.dumps([book.model_dump(mode="json") for book in books])
		try:
			with self._connect() as connection:
				connection.execute(
					"""
					INSERT INTO google_books_cache (query_key, books_json)
					VALUES (?, ?)
					ON CONFLICT(query_key) DO UPDATE SET books_json = excluded.books_json
					""",
					(query_key, payload),
				)
		except (sqlite3.Error, OSError) as error:
			raise GoogleBooksError("Unable to write Google Books cache") from error

	def _connect(self) -> sqlite3.Connection:
		return sqlite3.connect(self._database_path)

	@staticmethod
	def _normalize_query(query: str) -> str:
		normalized = " ".join(query.split()).casefold()
		if not normalized:
			raise ValueError("query must not be empty")
		return normalized