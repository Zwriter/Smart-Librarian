import pytest
from app.domain.chat_request import ChatRequest
from app.domain.conversation_message import ConversationMessage
from app.domain.recommendation import Recommendation
from pydantic import ValidationError


def test_chat_request_strips_question_and_preserves_history() -> None:
    request = ChatRequest(
        question="  Find a hopeful science-fiction book.  ",
        history=[ConversationMessage(role="user", content="  Hello  ")],
    )

    assert request.question == "Find a hopeful science-fiction book."
    assert request.history[0].content == "Hello"


def test_conversation_message_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        ConversationMessage(role="system", content="Instructions")


def test_chat_request_rejects_history_longer_than_limit() -> None:
    history = [ConversationMessage(role="user", content=str(index)) for index in range(21)]

    with pytest.raises(ValidationError):
        ChatRequest(question="Recommend a book", history=history)


def test_recommendation_requires_complete_fields() -> None:
    with pytest.raises(ValidationError):
        Recommendation(title="Dune", author="Frank Herbert", rationale="")