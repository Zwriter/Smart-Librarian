from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class OAuthAuthorizationRequest(BaseModel):
	model_config = ConfigDict(extra="forbid")

	state: str = Field(min_length=1)
	code_challenge: str = Field(min_length=1)
	redirect_uri: str = Field(min_length=1)
	scopes: tuple[str, ...] = Field(min_length=1)


class OAuthTokenSet(BaseModel):
	model_config = ConfigDict(extra="forbid")

	access_token: str = Field(min_length=1)
	refresh_token: str | None = None
	token_type: str = Field(min_length=1)
	expires_at: datetime | None = None
	granted_scopes: tuple[str, ...] = ()


class OAuthIdentity(BaseModel):
	model_config = ConfigDict(extra="forbid")

	provider: str = Field(min_length=1)
	subject: str = Field(min_length=1)
	email: str | None = None
	display_name: str | None = None


class ProviderBookReference(BaseModel):
	model_config = ConfigDict(extra="forbid")

	provider: str = Field(min_length=1)
	item_id: str = Field(min_length=1)


class LibraryVolume(BaseModel):
	model_config = ConfigDict(extra="forbid")

	reference: ProviderBookReference
	title: str = Field(min_length=1)
	authors: tuple[str, ...] = ()


class LibraryPage(BaseModel):
	model_config = ConfigDict(extra="forbid")

	items: tuple[LibraryVolume, ...] = ()
	total_items: int = Field(ge=0)


class OAuthProvider(Protocol):
	def build_authorization_url(self, request: OAuthAuthorizationRequest) -> str: ...

	def exchange_code(self, code: str, redirect_uri: str, code_verifier: str) -> OAuthTokenSet: ...

	def refresh_access_token(self, refresh_token: str) -> OAuthTokenSet: ...

	def get_identity(self, access_token: str) -> OAuthIdentity: ...


class PersonalLibraryProvider(Protocol):
	def list_volumes(
		self,
		access_token: str,
		shelf: str,
		start_index: int = 0,
		max_results: int = 10,
	) -> LibraryPage: ...

	def add_volume(self, access_token: str, shelf: str, volume_id: str) -> None: ...


class RefreshTokenCipher(Protocol):
	def encrypt(self, value: str) -> str: ...

	def decrypt(self, value: str) -> str: ...


class SessionStore(Protocol):
	def create(self, user_id: str, expires_at: datetime) -> str: ...

	def get_user_id(self, session_id: str, now: datetime) -> str | None: ...

	def revoke(self, session_id: str) -> None: ...