from app.api.dependencies import get_chat_service
from app.domain.chat_response import ChatResponse
from app.domain.recommendation import Recommendation
from app.main import create_app
from fastapi.testclient import TestClient


class FakeChatService:
	def recommend(self, request):
		assert request.question == "Find a book"
		return ChatResponse(
			recommendation=Recommendation(
				title="Dune",
				author="Frank Herbert",
				rationale="It matches the request.",
			),
			summary="A complete summary.",
		)


def test_chat_route_uses_dependency_override() -> None:
	application = create_app()
	application.dependency_overrides[get_chat_service] = lambda: FakeChatService()
	client = TestClient(application)

	response = client.post("/chat", json={"question": "Find a book"})

	assert response.status_code == 200
	assert response.json()["recommendation"]["title"] == "Dune"
	assert response.json()["summary"] == "A complete summary."


def test_chat_route_returns_stable_validation_error() -> None:
	client = TestClient(create_app())

	response = client.post("/chat", json={"question": ""})

	assert response.status_code == 422
	assert "detail" in response.json()


def test_chat_route_rejects_oversized_request_without_internal_details() -> None:
	application = create_app()
	client = TestClient(application)

	response = client.post(
		"/chat",
		content='{"question":"Find a book"}',
		headers={"Content-Length": "100001", "Content-Type": "application/json"},
	)

	assert response.status_code == 413
	assert response.json() == {"detail": "Request body exceeds the maximum allowed size."}
	assert "Traceback" not in response.text
	assert "C:\\" not in response.text