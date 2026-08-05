from pathlib import Path

from app.core.config import Settings
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

	assert response.status_code == 503
	assert response.json() == {"detail": "The application is not ready."}


def test_readiness_checks_configuration_and_vector_store(tmp_path: Path) -> None:
	book_data_path = tmp_path / "books.json"
	filter_config_path = tmp_path / "filter.json"
	book_data_path.write_text("[]", encoding="utf-8")
	filter_config_path.write_text("{}", encoding="utf-8")
	settings = Settings(
		_env_file=None,
		openai_api_key="test-key",
		book_data_path=book_data_path,
		filter_config_path=filter_config_path,
	)

	client = TestClient(create_app(settings, vector_store_factory=lambda path, name: object()))

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