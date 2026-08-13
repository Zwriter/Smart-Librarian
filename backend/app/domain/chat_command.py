from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QueryCommand(BaseModel):
	model_config = ConfigDict(extra="forbid")

	kind: Literal["query"]
	book_title: str = Field(min_length=1)


class SearchCommand(BaseModel):
	model_config = ConfigDict(extra="forbid")

	kind: Literal["search"]
	query: str = Field(min_length=1)


class MetadataCommand(BaseModel):
	model_config = ConfigDict(extra="forbid")

	kind: Literal["year", "author", "language"]
	book_title: str = Field(min_length=1)


ChatCommand = QueryCommand | SearchCommand | MetadataCommand