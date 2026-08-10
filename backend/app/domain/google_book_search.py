from app.domain.google_book import GoogleBook
from pydantic import BaseModel, ConfigDict, Field


class GoogleBookSearchResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	items: tuple[GoogleBook, ...]
	total: int = Field(ge=0)