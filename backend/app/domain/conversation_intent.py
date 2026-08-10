from typing import Literal

from pydantic import BaseModel, ConfigDict

ConversationIntentName = Literal[
	"greeting",
	"capabilities",
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
