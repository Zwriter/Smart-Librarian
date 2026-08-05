from app.domain.recommendation import Recommendation
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	recommendation: Recommendation
	summary: str = Field(min_length=1)

	@field_validator("summary", mode="before")
	@classmethod
	def strip_summary(cls, value: str) -> str:
		return value.strip()