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


def test_chat_response_accepts_three_compact_options() -> None:
    response = ChatResponse(
        recommendations=[
            {
                "title": "Dune",
                "author": "Frank Herbert",
                "summary": "Politics, ecology, and prophecy on desert worlds.",
            },
            {
                "title": "Foundation",
                "author": "Isaac Asimov",
                "summary": "A mathematician predicts civilization's long collapse.",
            },
            {
                "title": "Solaris",
                "author": "Stanislaw Lem",
                "summary": "A mysterious planet challenges human understanding.",
            },
        ],
        message="Would you like to know more about one specific book?",
    )

    assert len(response.recommendations) == 3


def test_chat_response_rejects_non_compact_option_summary() -> None:
    with pytest.raises(ValidationError):
        ChatResponse(
            recommendations=[
                {"title": "Dune", "author": "Frank Herbert", "summary": "Too short."},
                {
                    "title": "Foundation",
                    "author": "Isaac Asimov",
                    "summary": "A mathematician predicts civilization's long collapse.",
                },
                {
                    "title": "Solaris",
                    "author": "Stanislaw Lem",
                    "summary": "A mysterious planet challenges human understanding.",
                },
            ],
            message="Would you like to know more about one specific book?",
        )