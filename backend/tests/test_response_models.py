import pytest
from app.domain.chat_response import ChatResponse
from app.domain.recommendation import Recommendation
from pydantic import ValidationError


def test_chat_response_contains_recommendation_and_summary() -> None:
    response = ChatResponse(
        recommendation=Recommendation(
            title="Dune",
            author="Frank Herbert",
            rationale="It matches the requested themes.",
        ),
        summary="  A complete local summary.  ",
    )

    assert response.recommendation.title == "Dune"
    assert response.summary == "A complete local summary."


def test_chat_response_rejects_empty_summary() -> None:
    recommendation = Recommendation(
        title="Dune",
        author="Frank Herbert",
        rationale="It matches the requested themes.",
    )

    with pytest.raises(ValidationError):
        ChatResponse(recommendation=recommendation, summary="")