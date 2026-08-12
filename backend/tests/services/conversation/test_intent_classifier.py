import pytest
from app.core.exceptions import IntentClassificationError
from app.domain.chat_request import ChatRequest
from app.domain.conversation_intent import ConversationIntent
from app.services.conversation.intent_classifier import IntentClassifier
from app.services.llm.llm_client import ChatCompletionResult


class FakeLLMClient:
	def __init__(self, result: ChatCompletionResult) -> None:
		self.result = result
		self.messages = None

	def create_chat_completion(self, messages, tools=()):
		self.messages = messages
		assert tools == ()
		return self.result


def test_intent_classifier_parses_structured_result_and_passes_text_as_user_data() -> None:
	client = FakeLLMClient(
		ChatCompletionResult(
			content=(
				'{"intent":"capabilities","requires_retrieval":false,'
				'"requires_summary_tool":false,"book_title":null}'
			)
		)
	)
	classifier = IntentClassifier(client)  # type: ignore[arg-type]

	result = classifier.classify("wht cn u do?")

	assert result == ConversationIntent(
		intent="capabilities",
		requires_retrieval=False,
		requires_summary_tool=False,
		book_title=None,
	)
	assert client.messages[-1] == {"role": "user", "content": "wht cn u do?"}


def test_intent_classifier_includes_conversation_history() -> None:
	client = FakeLLMClient(
		ChatCompletionResult(
			content=(
				'{"intent":"book_summary","requires_retrieval":true,'
				'"requires_summary_tool":true,"book_title":"The Little Prince"}'
			)
		)
	)
	classifier = IntentClassifier(client)  # type: ignore[arg-type]

	classifier.classify(
		"Tell me more about it",
		ChatRequest(question="ignored").history,
	)

	assert client.messages[0]["role"] == "system"
	assert client.messages[-1]["content"] == "Tell me more about it"


def test_intent_classifier_accepts_search_action() -> None:
	client = FakeLLMClient(
		ChatCompletionResult(
			content=(
				'{"intent":"search","requires_retrieval":true,'
				'"requires_summary_tool":false,"book_title":"The Little Prince"}'
			)
		)
	)
	classifier = IntentClassifier(client)  # type: ignore[arg-type]

	result = classifier.classify("Tell me about The Little Prince")

	assert result.intent == "search"
	assert result.requires_retrieval is True
	assert result.book_title == "The Little Prince"


def test_intent_classifier_parses_ai_selected_response_language() -> None:
	client = FakeLLMClient(
		ChatCompletionResult(
			content=(
				'{"intent":"recommendation","requires_retrieval":true,'
				'"requires_summary_tool":false,"book_title":null,'
				'"response_language":"ro"}'
			)
		)
	)
	classifier = IntentClassifier(client)  # type: ignore[arg-type]

	result = classifier.classify("Recomandă-mi o carte despre natură umană")

	assert result.response_language == "ro"


@pytest.mark.parametrize(
	"result",
	[
		ChatCompletionResult(content="not-json"),
		ChatCompletionResult(content='{"intent":"unknown"}'),
		ChatCompletionResult(content=None),
	]
)
def test_intent_classifier_rejects_invalid_provider_results(result: ChatCompletionResult) -> None:
	classifier = IntentClassifier(FakeLLMClient(result))  # type: ignore[arg-type]

	with pytest.raises(IntentClassificationError):
		classifier.classify("hello")