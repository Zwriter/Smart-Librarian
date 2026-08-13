import re
from typing import cast

from app.domain.chat_command import ChatCommand, MetadataCommand, QueryCommand, SearchCommand


class ChatCommandParser:
	"""Parses supported slash commands without involving the language model."""

	_COMMAND_PATTERN = re.compile(
		r"^/(?P<name>query|search|year|author|language)\s*(?P<value>.*)$", re.I
	)

	def parse(self, question: str) -> ChatCommand | None:
		match = self._COMMAND_PATTERN.match(question.strip())
		if match is None:
			return None

		name = match.group("name").casefold()
		value = match.group("value").strip()
		if not value:
			return None
		if name == "query":
			return QueryCommand(kind="query", book_title=value)
		if name == "search":
			return SearchCommand(kind="search", query=value)
		return cast(
			MetadataCommand,
			MetadataCommand.model_validate({"kind": name, "book_title": value}),
		)