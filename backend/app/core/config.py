from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=(BACKEND_ROOT.parent / ".env", BACKEND_ROOT / ".env"),
		env_file_encoding="utf-8",
		extra="ignore",
		case_sensitive=False,
	)

	openai_api_key: SecretStr = Field(min_length=1)
	openai_chat_model: str = Field(default="gpt-4o-mini", min_length=1)
	openai_embedding_model: str = Field(default="text-embedding-3-small", min_length=1)
	chroma_persist_directory: Path = BACKEND_ROOT / ".chroma"
	chroma_collection_name: str = Field(default="books", min_length=1)
	book_data_path: Path = BACKEND_ROOT / "data" / "book_summaries.json"
	filter_config_path: Path = BACKEND_ROOT / "data" / "filter_config.json"
	cors_allowed_origins: list[str] = Field(
		default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
	)
	top_k_results: int = Field(default=5, gt=0, le=20)
	max_question_length: int = Field(default=2_000, gt=0)
	max_history_messages: int = Field(default=20, gt=0)
	log_level: str = Field(default="INFO", min_length=1)
	log_console_enabled: bool = True
	log_file_enabled: bool = True
	log_file_path: Path = BACKEND_ROOT / "logs" / "app.log"
	log_max_bytes: int = Field(default=10_000_000, gt=0)
	log_backup_count: int = Field(default=5, ge=0)
	log_privacy_mode: Literal["redact"] = "redact"
	model_pricing: dict[str, dict[str, float]] = Field(default_factory=dict)

	@field_validator(
		"openai_chat_model",
		"openai_embedding_model",
		"chroma_collection_name",
		mode="before",
	)
	@classmethod
	def strip_text_values(cls, value: str) -> str:
		return value.strip()

	@field_validator("cors_allowed_origins", mode="before")
	@classmethod
	def validate_origins(cls, value: list[str]) -> list[str]:
		origins = [origin.strip().rstrip("/") for origin in value]
		if not origins or any(not origin for origin in origins):
			raise ValueError("cors_allowed_origins must contain at least one non-empty origin")
		return origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()
