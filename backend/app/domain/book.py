from pydantic import BaseModel, ConfigDict, Field, field_validator


class Book(BaseModel):
	model_config = ConfigDict(extra="forbid")

	title: str = Field(min_length=1)
	author: str = Field(min_length=1)
	summary: str = Field(min_length=1)
	description: str | None = None
	metadata: dict[str, str] = Field(default_factory=dict)

	@field_validator("title", "author", "summary", "description", mode="before")
	@classmethod
	def strip_text_values(cls, value: str | None) -> str | None:
		return value.strip() if value is not None else None