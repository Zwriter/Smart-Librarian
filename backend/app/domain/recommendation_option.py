from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendationOption(BaseModel):
	model_config = ConfigDict(extra="forbid")

	title: str = Field(min_length=1)
	author: str = Field(min_length=1)
	summary: str = Field(min_length=1)

	@field_validator("title", "author", "summary", mode="before")
	@classmethod
	def strip_text_values(cls, value: str) -> str:
		return value.strip()

	@field_validator("summary")
	@classmethod
	def require_five_to_ten_words(cls, value: str) -> str:
		word_count = len(value.split())
		if not 5 <= word_count <= 10:
			raise ValueError("summary must contain between 5 and 10 words")
		return value