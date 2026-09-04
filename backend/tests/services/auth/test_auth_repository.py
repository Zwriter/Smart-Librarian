from datetime import UTC, datetime, timedelta

import pytest
from app.services.auth.auth_repository import SQLiteAuthRepository
from app.services.auth.contracts import OAuthIdentity
from app.services.auth.crypto import RefreshTokenCipher
from cryptography.fernet import Fernet


def test_refresh_token_cipher_round_trip() -> None:
	cipher = RefreshTokenCipher(Fernet.generate_key().decode("ascii"))

	encrypted = cipher.encrypt("refresh-token")

	assert encrypted != "refresh-token"
	assert cipher.decrypt(encrypted) == "refresh-token"


def test_refresh_token_cipher_rejects_invalid_key() -> None:
	with pytest.raises(ValueError, match="valid Fernet key"):
		RefreshTokenCipher("invalid")


def test_auth_repository_reuses_provider_identity_and_expires_sessions(tmp_path) -> None:
	repository = SQLiteAuthRepository(tmp_path / "auth.sqlite3")
	identity = OAuthIdentity(provider="google", subject="subject-1", email="user@example.com")

	first_user_id = repository.create_user_for_identity(identity)
	second_user_id = repository.create_user_for_identity(identity)
	session_id = repository.create_session(
		first_user_id,
		datetime.now(UTC) + timedelta(minutes=5),
	)

	assert first_user_id == second_user_id
	assert repository.get_user_id(session_id, datetime.now(UTC)) == first_user_id
	assert repository.get_user_id(session_id, datetime.now(UTC) + timedelta(minutes=6)) is None


def test_auth_repository_revokes_sessions(tmp_path) -> None:
	repository = SQLiteAuthRepository(tmp_path / "auth.sqlite3")
	user_id = repository.create_user_for_identity(
		OAuthIdentity(provider="google", subject="subject-2")
	)
	session_id = repository.create_session(
		user_id,
		datetime.now(UTC) + timedelta(minutes=5),
	)

	repository.revoke_session(session_id)

	assert repository.get_user_id(session_id, datetime.now(UTC)) is None