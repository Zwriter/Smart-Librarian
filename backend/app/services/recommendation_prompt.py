from collections.abc import Sequence
from typing import Any

from app.domain.conversation_message import ConversationMessage
from app.domain.retrieved_book import RetrievedBook

RECOMMENDATION_SYSTEM_PROMPT = (
	"You are a thoughtful book recommendation assistant. Recommend one book using "
	"the retrieved catalogue context and the user's question. Do not invent book "
	"details. Explain briefly why the recommendation fits. After choosing a book, "
	"call get_summary_by_title to retrieve its complete local summary."
)

GET_SUMMARY_TOOL: dict[str, Any] = {
	"type": "function",
	"function": {
		"name": "get_summary_by_title",
		"description": "Return the complete local summary for a recommended book title.",
		"parameters": {
			"type": "object",
			"properties": {
				"title": {
					"type": "string",
					"description": "The exact title of the recommended book.",
				}
			},
			"required": ["title"],
			"additionalProperties": False,
		},
	},
}


def build_recommendation_messages(
	question: str,
	history: Sequence[ConversationMessage],
	retrieved_books: Sequence[RetrievedBook],
) -> list[dict[str, str]]:
	"""Build the complete provider-neutral message list for recommendations."""
	context = "\n\n".join(
		f"Title: {retrieved.book.title}\n"
		f"Author: {retrieved.book.author}\n"
		f"Summary: {retrieved.book.summary}"
		for retrieved in retrieved_books
	)
	context_message = (
		"Retrieved catalogue context:\n"
		f"{context if context else 'No catalogue books were retrieved.'}"
	)

	return [
		{"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
		*(
			{"role": message.role, "content": message.content}
			for message in history
		),
		{"role": "system", "content": context_message},
		{"role": "user", "content": question},
	]