from app.domain.conversation_message import ConversationMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
	model_config = ConfigDict(extra="forbid")

	question: str = Field(min_length=1, max_length=2_000)
	history: list[ConversationMessage] = Field(default_factory=list, max_length=20)

	@field_validator("question", mode="before")
	@classmethod
	def strip_question(cls, value: str) -> str:
		return value.strip()