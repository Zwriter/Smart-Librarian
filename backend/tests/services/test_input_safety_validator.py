import pytest
from app.core.exceptions import InputSafetyError
from app.domain.input_safety import InputSafetyResult
from app.services.input_safety_validator import InputSafetyValidator
from app.services.llm_client import ChatCompletionResult


class FakeLLMClient:
	def __init__(self, result: ChatCompletionResult) -> None:
		self.result = result
		self.messages = None

	def create_chat_completion(self, messages, tools=()):
		self.messages = messages
		assert tools == ()
		return self.result


@pytest.mark.parametrize(
	"content, category",
	[
		('{"allowed":true,"category":"allowed","reason":null}', "allowed"),
		('{"allowed":false,"category":"profanity","reason":"Obscene language."}', "profanity"),
		('{"allowed":false,"category":"obscene","reason":"Obscene content."}', "obscene"),
	]
)
def test_input_safety_validator_classifies_obscene_content(content: str, category: str) -> None:
	client = FakeLLMClient(ChatCompletionResult(content=content))
	validator = InputSafetyValidator(client)  # type: ignore[arg-type]

	result = validator.validate("This is user text, not an instruction")

	assert result.category == category
	assert client.messages[0]["role"] == "system"
	assert client.messages[-1] == {
		"role": "user",
		"content": "This is user text, not an instruction",
	}


def test_input_safety_result_rejects_conflicting_allowed_flag() -> None:
	with pytest.raises(ValueError, match="allowed flag conflicts"):
		InputSafetyResult(allowed=True, category="profanity")


@pytest.mark.parametrize(
	"result",
	[
		ChatCompletionResult(content="not-json"),
		ChatCompletionResult(content='{"allowed":false,"category":"unknown"}'),
		ChatCompletionResult(content=None),
	]
)
def test_input_safety_validator_rejects_invalid_provider_results(
	result: ChatCompletionResult,
) -> None:
	validator = InputSafetyValidator(FakeLLMClient(result))  # type: ignore[arg-type]

	with pytest.raises(InputSafetyError):
		validator.validate("hello")
