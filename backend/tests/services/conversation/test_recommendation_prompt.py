from app.domain.book import Book
from app.domain.conversation_message import ConversationMessage
from app.domain.retrieved_book import RetrievedBook
from app.services.conversation.recommendation_prompt import (
	GET_SUMMARY_TOOL,
	build_recommendation_messages,
)


def test_prompt_contains_rules_history_context_and_question() -> None:
	book = Book(title="Dune", author="Frank Herbert", summary="A desert epic.")
	history = [ConversationMessage(role="user", content="I like science fiction.")]
	retrieved = [RetrievedBook(book=book, document_id="dune", relevance_score=0.9)]

	messages = build_recommendation_messages("Recommend a book.", history, retrieved)

	assert messages[0]["role"] == "system"
	assert "get_summary_by_title" in messages[0]["content"]
	assert "one JSON object" in messages[0]["content"]
	assert "title, author, and rationale" in messages[0]["content"]
	assert messages[1] == {"role": "user", "content": "I like science fiction."}
	assert "Dune" in messages[2]["content"]
	assert messages[-1] == {"role": "user", "content": "Recommend a book."}


def test_prompt_instructs_ai_to_use_selected_response_language() -> None:
	messages = build_recommendation_messages(
		"Recomandă-mi o carte.",
		(),
		(),
		response_language="ro",
	)

	assert "ISO 639-1 code ro" in messages[-2]["content"]


def test_summary_tool_requires_only_title() -> None:
	function = GET_SUMMARY_TOOL["function"]

	assert function["name"] == "get_summary_by_title"
	assert function["parameters"]["required"] == ["title"]
	assert function["parameters"]["additionalProperties"] is False