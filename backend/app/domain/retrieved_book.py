from app.domain.book import Book
from pydantic import BaseModel, ConfigDict, Field


class RetrievedBook(BaseModel):
	model_config = ConfigDict(extra="forbid")

	book: Book
	document_id: str = Field(min_length=1)
	relevance_score: float = Field(ge=0)