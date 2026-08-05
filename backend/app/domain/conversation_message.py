from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationMessage(BaseModel):
	model_config = ConfigDict(extra="forbid")

	role: Literal["user", "assistant"]
	content: str = Field(min_length=1, max_length=10_000)

	@field_validator("content", mode="before")
	@classmethod
	def strip_content(cls, value: str) -> str:
		return value.strip()