from collections.abc import Sequence
from typing import Any

from app.domain.conversation_message import ConversationMessage
from app.domain.retrieved_book import RetrievedBook

RECOMMENDATION_SYSTEM_PROMPT = (
	"You are a thoughtful librarian for a book catalogue. Only recommend a "
	"book when the user asks for a recommendation or asks about a book represented "
	"in the retrieved catalogue context. Retrieved context may include clearly "
	"labeled Google Books external metadata. For greetings, casual conversation, or "
	"questions unrelated to recommendations, do not recommend a book; return one "
	"JSON object with exactly this string field: message. If the user asks about a "
	"specific book that is not in the retrieved context, do not substitute a similar "
	"book; return a concise message saying you do not know that book. For broad or "
	"ambiguous requests, return exactly three catalogue books in one JSON object "
	"with fields recommendations and message. Each recommendation must contain "
	"title, author, and a summary of exactly 5 to 10 words. The message must ask "
	"whether the user wants to know more about a specific book. Do not call the "
	"summary tool for this multi-book response. Never invent book details. For a "
	"specific recommendation, return one JSON object with exactly these string "
	"fields: title, author, and rationale. Only call get_summary_by_title for a "
	"local catalogue title, never for a Google Books external metadata result. Do "
	"not return markdown or prose outside JSON."
)

AMBIGUOUS_REQUEST_INSTRUCTION = (
	"The user's request is intentionally broad. Return exactly three catalogue "
	"recommendations with title, author, and 5 to 10 word summaries, plus a message "
	"asking whether they want to know more about one specific book. Do not call tools."
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
	ambiguous: bool = False,
	previous_titles: set[str] | None = None,
	response_language: str | None = None,
) -> list[dict[str, str]]:
	"""Build the complete provider-neutral message list for recommendations."""
	context = "\n\n".join(
		f"Source: {_source_label(retrieved)}\n"
		f"Title: {retrieved.book.title}\n"
		f"Author: {retrieved.book.author}\n"
		f"Summary: {retrieved.book.summary}"
		for retrieved in retrieved_books
	)
	context_message = (
		"Retrieved catalogue context:\n"
		f"{context if context else 'No catalogue books were retrieved.'}"
	)
	language_instruction = (
		f"Respond entirely in the language identified by ISO 639-1 code "
		f"{response_language}. Keep book titles and author names in their original form."
		if response_language
		else "Respond in the language used by the user's latest message."
	)

	messages = [
		{"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
		*(
			{"role": message.role, "content": message.content}
			for message in history
		),
		{"role": "system", "content": context_message},
		{"role": "system", "content": language_instruction},
		{"role": "user", "content": question},
	]
	if ambiguous:
		instruction = AMBIGUOUS_REQUEST_INSTRUCTION
		if previous_titles:
			instruction += (
				" Avoid repeating any titles already recommended in the conversation "
				"when at least three fresh catalogue choices are available."
			)
		messages.insert(-1, {"role": "system", "content": instruction})
	return messages


def _source_label(retrieved: RetrievedBook) -> str:
	if retrieved.book.metadata.get("source") == "google_books":
		return "Google Books (external metadata)"
	return "Local catalogue"