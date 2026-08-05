import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_settings_use_backend_defaults() -> None:
    settings = Settings(_env_file=None, openai_api_key="test-key")

    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.top_k_results == 5
    assert settings.book_data_path.name == "book_summaries.json"


def test_settings_reject_missing_api_key() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_invalid_retrieval_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="test-key", top_k_results=0)


def test_settings_reject_empty_cors_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="test-key", cors_allowed_origins=[""])