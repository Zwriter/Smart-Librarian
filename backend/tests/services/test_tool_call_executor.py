import pytest
from app.core.exceptions import ToolCallError
from app.services.llm_client import ToolCall
from app.services.tool_call_executor import ToolCallExecutor


def test_executor_validates_and_dispatches_summary_tool() -> None:
	requested_titles: list[str] = []
	executor = ToolCallExecutor(
		lambda title: requested_titles.append(title) or "Complete summary."
	)

	result = executor.execute(
		ToolCall(
			id="call-1",
			name="get_summary_by_title",
			arguments='{"title": "  Dune  "}',
		)
	)

	assert result == "Complete summary."
	assert requested_titles == ["Dune"]


@pytest.mark.parametrize(
	"tool_call, message",
	[
		(
			ToolCall(id="call-1", name="unknown", arguments='{"title":"Dune"}'),
			"Unknown tool",
		),
		(
			ToolCall(id="call-1", name="get_summary_by_title", arguments="not-json"),
			"valid JSON",
		),
		(
			ToolCall(id="call-1", name="get_summary_by_title", arguments="[]"),
			"JSON object",
		),
		(
			ToolCall(
				id="call-1",
				name="get_summary_by_title",
				arguments='{"title":"Dune","extra":1}',
			),
			"unknown fields",
		),
	],
)
def test_executor_rejects_invalid_tool_calls(tool_call: ToolCall, message: str) -> None:
	executor = ToolCallExecutor(lambda title: "Summary.")

	with pytest.raises(ToolCallError, match=message):
		executor.execute(tool_call)


def test_executor_rejects_tool_call_loop() -> None:
	executor = ToolCallExecutor(lambda title: "Summary.", max_call_depth=1)
	tool_call = ToolCall(id="call-1", name="get_summary_by_title", arguments='{"title":"Dune"}')

	with pytest.raises(ToolCallError, match="depth limit"):
		executor.execute(tool_call, call_depth=1)