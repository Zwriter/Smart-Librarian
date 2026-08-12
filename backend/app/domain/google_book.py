from pydantic import BaseModel, ConfigDict, Field


class GoogleBook(BaseModel):
	"""Normalized public book metadata returned by Google Books."""

	model_config = ConfigDict(extra="forbid")

	volume_id: str = Field(min_length=1)
	title: str = Field(min_length=1)
	authors: tuple[str, ...] = ()
	description: str | None = None
	published_date: str | None = None
	publisher: str | None = None
	language: str | None = None
	categories: tuple[str, ...] = ()
	thumbnail_url: str | None = None
	isbn_10: str | None = None
	isbn_13: str | None = None