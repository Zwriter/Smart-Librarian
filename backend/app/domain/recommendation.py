from pydantic import BaseModel, ConfigDict, Field, field_validator


class Recommendation(BaseModel):
	model_config = ConfigDict(extra="forbid")

	title: str = Field(min_length=1)
	author: str = Field(min_length=1)
	rationale: str = Field(min_length=1)
	published_date: str | None = None
	publisher: str | None = None
	language: str | None = None

	@field_validator("title", "author", "rationale", mode="before")
	@classmethod
	def strip_text_values(cls, value: str) -> str:
		return value.strip()