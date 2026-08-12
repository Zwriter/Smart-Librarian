from typing import Any, Protocol

import httpx
from app.core.exceptions import GoogleBooksError
from app.domain.google_book import GoogleBook
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class GoogleBooksClient(Protocol):
	"""Provider-neutral interface for public Google Books searches."""

	def search_volumes(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		...


class _VolumeInfo(BaseModel):
	model_config = ConfigDict(extra="ignore")

	title: str = Field(min_length=1)
	authors: list[str] = Field(default_factory=list)
	description: str | None = None
	published_date: str | None = Field(default=None, validation_alias="publishedDate")
	publisher: str | None = None
	language: str | None = None
	categories: list[str] = Field(default_factory=list)
	image_links: dict[str, str] = Field(default_factory=dict, validation_alias="imageLinks")
	industry_identifiers: list[dict[str, str]] = Field(
		default_factory=list,
		validation_alias="industryIdentifiers",
	)


class _Volume(BaseModel):
	model_config = ConfigDict(extra="ignore")

	id: str = Field(min_length=1)
	volume_info: _VolumeInfo = Field(validation_alias="volumeInfo")


class _SearchResponse(BaseModel):
	model_config = ConfigDict(extra="ignore")

	items: list[_Volume] = Field(default_factory=list)


class GoogleBooksApiClient:
	"""Calls Google Books and maps provider payloads to domain models."""

	def __init__(
		self,
		base_url: str = "https://www.googleapis.com/books/v1",
		timeout_seconds: float = 10.0,
		max_results: int = 10,
		api_key: str | None = None,
		client: httpx.Client | None = None,
	) -> None:
		if timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be positive")
		if not 1 <= max_results <= 40:
			raise ValueError("max_results must be between 1 and 40")
		self._base_url = base_url.rstrip("/")
		self._timeout_seconds = timeout_seconds
		self._max_results = max_results
		self._api_key = api_key
		self._client = client or httpx.Client()

	def search_volumes(self, query: str, limit: int) -> tuple[GoogleBook, ...]:
		if not query.strip():
			raise ValueError("query must not be empty")
		if limit < 1:
			raise ValueError("limit must be positive")

		params: dict[str, Any] = {"q": query.strip(), "maxResults": min(limit, self._max_results)}
		if self._api_key:
			params["key"] = self._api_key
		try:
			response = self._client.get(
				f"{self._base_url}/volumes",
				params=params,
				timeout=self._timeout_seconds,
			)
			response.raise_for_status()
			payload = _SearchResponse.model_validate(response.json())
			return tuple(self._map_volume(volume) for volume in payload.items)
		except (httpx.HTTPError, ValueError, ValidationError, TypeError) as error:
			raise GoogleBooksError("Google Books search failed") from error

	@staticmethod
	def _map_volume(volume: _Volume) -> GoogleBook:
		identifiers = {
			item.get("type"): item.get("identifier")
			for item in volume.volume_info.industry_identifiers
			if item.get("type") and item.get("identifier")
		}
		return GoogleBook(
			volume_id=volume.id,
			title=volume.volume_info.title,
			authors=tuple(volume.volume_info.authors),
			description=volume.volume_info.description,
			published_date=volume.volume_info.published_date,
			publisher=volume.volume_info.publisher,
			language=volume.volume_info.language,
			categories=tuple(volume.volume_info.categories),
			thumbnail_url=volume.volume_info.image_links.get("thumbnail"),
			isbn_10=identifiers.get("ISBN_10"),
			isbn_13=identifiers.get("ISBN_13"),
		)