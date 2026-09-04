from typing import cast

from cryptography.fernet import Fernet, InvalidToken


class RefreshTokenCipher:
	"""Encrypts provider refresh tokens using an application Fernet key."""

	def __init__(self, key: str) -> None:
		try:
			self._fernet = Fernet(key.encode("ascii"))
		except (ValueError, TypeError, UnicodeEncodeError) as error:
			raise ValueError("auth encryption key must be a valid Fernet key") from error

	def encrypt(self, value: str) -> str:
		if not value:
			raise ValueError("refresh token must not be empty")
		return cast(bytes, self._fernet.encrypt(value.encode("utf-8"))).decode("ascii")

	def decrypt(self, value: str) -> str:
		try:
			return cast(bytes, self._fernet.decrypt(value.encode("ascii"))).decode("utf-8")
		except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError) as error:
			raise ValueError("refresh token could not be decrypted") from error