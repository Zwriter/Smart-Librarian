from app.services.summary_tool import SummaryTool


class FakeRepository:
	def __init__(self) -> None:
		self.title: str | None = None

	def get_summary_by_title(self, title: str) -> str:
		self.title = title
		return "Complete local summary."


def test_summary_tool_delegates_to_repository() -> None:
	repository = FakeRepository()
	tool = SummaryTool(repository)  # type: ignore[arg-type]

	assert tool.get_summary_by_title("Dune") == "Complete local summary."
	assert repository.title == "Dune"