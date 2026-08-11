from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

ConversationIntentName = Literal[
	"greeting",
	"capabilities",
	"search",
	"recommendation",
	"book_summary",
	"clarification",
	"general_conversation",
	"unsupported",
]


class ConversationIntent(BaseModel):
	model_config = ConfigDict(extra="forbid")

	intent: ConversationIntentName
	requires_retrieval: bool
	requires_summary_tool: bool
	book_title: str | None = None

	@field_validator("book_title", mode="before")
	@classmethod
	def strip_book_title(cls, value: str | None) -> str | None:
		return value.strip() if value is not None else None
