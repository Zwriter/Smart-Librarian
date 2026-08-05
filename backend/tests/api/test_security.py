from pathlib import Path

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_readiness_failure_does_not_expose_internal_path(tmp_path: Path) -> None:
	settings = Settings(
		_env_file=None,
		openai_api_key="test-key",
		book_data_path=tmp_path / "private-books.json",
		filter_config_path=tmp_path / "private-filter.json",
	)

	response = TestClient(create_app(settings)).get("/ready")

	assert response.status_code == 503
	assert response.json() == {"detail": "The application is not ready."}
	assert "private-books" not in response.text
	assert "Traceback" not in response.text