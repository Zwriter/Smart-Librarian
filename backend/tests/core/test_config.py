import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_settings_use_backend_defaults() -> None:
    settings = Settings(_env_file=None, openai_api_key="test-key")

    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.top_k_results == 5
    assert settings.book_data_path.name == "book_summaries.json"
    assert settings.log_level == "INFO"
    assert settings.log_console_enabled is True
    assert settings.log_file_enabled is True
    assert settings.log_privacy_mode == "redact"


def test_settings_reject_missing_api_key() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_invalid_retrieval_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="test-key", top_k_results=0)


def test_settings_reject_empty_cors_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="test-key", cors_allowed_origins=[""])


def test_settings_reject_privacy_mode_that_disables_redaction() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="test-key", log_privacy_mode="plain")


def test_settings_reject_wildcard_cors_origin() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openai_api_key="test-key", cors_allowed_origins=["*"])


def test_settings_resolve_repository_relative_paths() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="test-key",
        book_data_path="backend/data/book_summaries.json",
        filter_config_path="backend/data/filter_config.json",
    )

    assert settings.book_data_path.is_file()
    assert settings.filter_config_path.is_file()