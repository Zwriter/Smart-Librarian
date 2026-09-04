from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=BACKEND_ROOT / ".env",
		env_file_encoding="utf-8",
		extra="ignore",
		case_sensitive=False,
	)

	openai_api_key: SecretStr = Field(min_length=1)
	openai_chat_model: str = Field(default="gpt-4o-mini", min_length=1)
	openai_validation_model: str = Field(default="gpt-4o-mini", min_length=1)
	openai_embedding_model: str = Field(default="text-embedding-3-small", min_length=1)
	google_books_api_key: SecretStr | None = None
	google_books_base_url: str = Field(
		default="https://www.googleapis.com/books/v1",
		min_length=1,
	)
	google_books_timeout_seconds: float = Field(default=10.0, gt=0)
	google_books_max_results: int = Field(default=10, gt=0, le=40)
	google_books_cache_path: Path = BACKEND_ROOT / ".google_books_cache.sqlite3"
	google_books_collection_name: str = Field(default="google_books", min_length=1)
	google_oauth_client_id: str | None = None
	google_oauth_client_secret: SecretStr | None = None
	google_oauth_redirect_uri: str = Field(
		default="http://localhost:8000/auth/google/callback",
		min_length=1,
	)
	google_oauth_frontend_redirect_uri: str = Field(
		default="http://localhost:5173",
		min_length=1,
	)
	google_oauth_identity_scopes: list[str] = Field(
		default_factory=lambda: [
			"openid",
			"https://www.googleapis.com/auth/userinfo.email",
			"https://www.googleapis.com/auth/userinfo.profile",
		]
	)
	google_oauth_books_scope: str = "https://www.googleapis.com/auth/books"
	google_books_library_shelf: str = Field(default="0", min_length=1)
	auth_database_path: Path = BACKEND_ROOT / ".auth.sqlite3"
	auth_session_cookie_name: str = Field(default="smart_librarian_session", min_length=1)
	auth_session_ttl_seconds: int = Field(default=86_400, gt=0)
	auth_oauth_transaction_ttl_seconds: int = Field(default=600, gt=0)
	auth_cookie_secure: bool = False
	auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
	auth_encryption_key: SecretStr | None = None
	chroma_persist_directory: Path = BACKEND_ROOT / ".chroma"
	chroma_collection_name: str = Field(default="books", min_length=1)
	book_data_path: Path = BACKEND_ROOT / "data" / "book_summaries.json"
	filter_config_path: Path = BACKEND_ROOT / "data" / "filter_config.json"
	cors_allowed_origins: list[str] = Field(
		default_factory=lambda: [
			"http://localhost:5173",
			"http://127.0.0.1:5173",
			"http://localhost:3000",
			"http://127.0.0.1:3000",
		]
	)
	top_k_results: int = Field(default=5, gt=0, le=20)
	max_question_length: int = Field(default=2_000, gt=0)
	max_history_messages: int = Field(default=20, gt=0)
	max_request_body_bytes: int = Field(default=100_000, gt=0)
	log_level: str = Field(default="INFO", min_length=1)
	log_console_enabled: bool = True
	log_file_enabled: bool = True
	log_file_path: Path = BACKEND_ROOT / "logs" / "app.log"
	log_max_bytes: int = Field(default=10_000_000, gt=0)
	log_backup_count: int = Field(default=5, ge=0)
	log_privacy_mode: Literal["redact"] = "redact"
	model_pricing: dict[str, dict[str, float]] = Field(default_factory=dict)

	@field_validator(
		"chroma_persist_directory",
		"book_data_path",
		"filter_config_path",
		"google_books_cache_path",
		"auth_database_path",
		"log_file_path",
		mode="before",
	)
	@classmethod
	def resolve_paths(cls, value: Path) -> Path:
		path = Path(value)
		if path.is_absolute():
			return path
		parts = path.parts
		base = BACKEND_ROOT.parent if parts and parts[0] == "backend" else BACKEND_ROOT
		return base / path

	@field_validator(
		"openai_chat_model",
		"openai_validation_model",
		"openai_embedding_model",
		"google_books_base_url",
		"google_books_collection_name",
		"chroma_collection_name",
		"google_oauth_client_id",
		"google_oauth_redirect_uri",
		"google_oauth_frontend_redirect_uri",
		"google_oauth_books_scope",
		"google_books_library_shelf",
		"auth_session_cookie_name",
		mode="before",
	)
	@classmethod
	def strip_text_values(cls, value: str | None) -> str | None:
		return value.strip() if value is not None else None

	@field_validator("cors_allowed_origins", mode="before")
	@classmethod
	def validate_origins(cls, value: list[str]) -> list[str]:
		origins = [origin.strip().rstrip("/") for origin in value]
		if not origins or any(not origin or origin == "*" for origin in origins):
			raise ValueError("cors_allowed_origins must contain at least one non-empty origin")
		return origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()
