from app.main import create_app
from fastapi.testclient import TestClient


def test_health_endpoint() -> None:
	client = TestClient(create_app())

	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


def test_readiness_endpoint() -> None:
	client = TestClient(create_app())

	response = client.get("/ready")

	assert response.status_code == 200
	assert response.json() == {"status": "ready"}


def test_cors_uses_explicit_default_origins() -> None:
	client = TestClient(create_app())

	response = client.options(
		"/health",
		headers={
			"Origin": "http://localhost:5173",
			"Access-Control-Request-Method": "GET",
		},
	)

	assert response.status_code == 200
	assert response.headers["access-control-allow-origin"] == "http://localhost:5173"