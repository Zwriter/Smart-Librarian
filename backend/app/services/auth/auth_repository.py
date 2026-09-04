import hashlib
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.core.exceptions import AuthPersistenceError
from app.services.auth.contracts import OAuthIdentity


class SQLiteAuthRepository:
	"""Stores private authentication state in a dedicated SQLite database."""

	def __init__(self, database_path: Path) -> None:
		self._database_path = database_path
		try:
			self._database_path.parent.mkdir(parents=True, exist_ok=True)
			with self._connect() as connection:
				connection.executescript(
					"""
					CREATE TABLE IF NOT EXISTS users (
						id TEXT PRIMARY KEY,
						created_at TEXT NOT NULL
					);
					CREATE TABLE IF NOT EXISTS provider_identities (
						provider TEXT NOT NULL,
						subject TEXT NOT NULL,
						user_id TEXT NOT NULL REFERENCES users(id),
						email TEXT,
						display_name TEXT,
						PRIMARY KEY (provider, subject)
					);
					CREATE TABLE IF NOT EXISTS oauth_transactions (
						state_hash TEXT PRIMARY KEY,
						code_verifier TEXT NOT NULL,
						redirect_uri TEXT NOT NULL,
						scopes_json TEXT NOT NULL,
						expires_at TEXT NOT NULL,
						consumed_at TEXT
					);
					CREATE TABLE IF NOT EXISTS sessions (
						session_hash TEXT PRIMARY KEY,
						user_id TEXT NOT NULL REFERENCES users(id),
						expires_at TEXT NOT NULL,
						revoked_at TEXT
					);
					CREATE TABLE IF NOT EXISTS refresh_tokens (
						user_id TEXT PRIMARY KEY REFERENCES users(id),
						encrypted_token TEXT NOT NULL,
						granted_scopes_json TEXT NOT NULL,
						revoked_at TEXT
					);
					"""
				)
		except (OSError, sqlite3.Error) as error:
			raise AuthPersistenceError("Unable to initialize authentication storage") from error

	def create_user_for_identity(self, identity: OAuthIdentity) -> str:
		try:
			with self._connect() as connection:
				row = connection.execute(
					"SELECT user_id FROM provider_identities WHERE provider = ? AND subject = ?",
					(identity.provider, identity.subject),
				).fetchone()
				if row is not None:
					return str(row[0])
				user_id = secrets.token_urlsafe(24)
				connection.execute(
					"INSERT INTO users (id, created_at) VALUES (?, ?)",
					(user_id, _utc_now()),
				)
				connection.execute(
					"INSERT INTO provider_identities "
					"(provider, subject, user_id, email, display_name) VALUES (?, ?, ?, ?, ?)",
					(
						identity.provider,
						identity.subject,
						user_id,
						identity.email,
						identity.display_name,
					),
				)
				return user_id
		except sqlite3.Error as error:
			raise AuthPersistenceError("Unable to persist authentication identity") from error

	def create_session(self, user_id: str, expires_at: datetime) -> str:
		session_id = secrets.token_urlsafe(32)
		try:
			with self._connect() as connection:
				connection.execute(
					"INSERT INTO sessions (session_hash, user_id, expires_at) VALUES (?, ?, ?)",
					(_hash(session_id), user_id, expires_at.isoformat()),
				)
			return session_id
		except sqlite3.Error as error:
			raise AuthPersistenceError("Unable to create authentication session") from error

	def get_user_id(self, session_id: str, now: datetime) -> str | None:
		try:
			with self._connect() as connection:
				row = connection.execute(
					"SELECT user_id, expires_at, revoked_at FROM sessions WHERE session_hash = ?",
					(_hash(session_id),),
				).fetchone()
			if row is None or row[2] is not None or datetime.fromisoformat(row[1]) <= now:
				return None
			return str(row[0])
		except (sqlite3.Error, ValueError) as error:
			raise AuthPersistenceError("Unable to read authentication session") from error

	def revoke_session(self, session_id: str) -> None:
		try:
			with self._connect() as connection:
				connection.execute(
					"UPDATE sessions SET revoked_at = ? WHERE session_hash = ?",
					(_utc_now(), _hash(session_id)),
				)
		except sqlite3.Error as error:
			raise AuthPersistenceError("Unable to revoke authentication session") from error

	def _connect(self) -> sqlite3.Connection:
		connection = sqlite3.connect(self._database_path)
		connection.execute("PRAGMA foreign_keys = ON")
		return connection


def _hash(value: str) -> str:
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_now() -> str:
	return datetime.now(UTC).isoformat()