import { useRef, useState } from 'react'
import { sendChatRequest } from '../services/chatApi'
import { frontendConfig } from '../config'
import type { ChatResponse, ConversationMessage } from '../types/api'
import type { ErrorState, RequestStatus } from '../types/ui'

export function useChat() {
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<ChatResponse | null>(null)
  const [validationError, setValidationError] = useState<ErrorState['error']>(null)
  const [apiError, setApiError] = useState<ErrorState['error']>(null)
  const [status, setStatus] = useState<RequestStatus>('idle')
  const [failedRequest, setFailedRequest] = useState<{ question: string; history: ConversationMessage[] } | null>(null)
  const requestInFlight = useRef(false)

  const error = validationError ?? apiError

  async function executeRequest(
    nextQuestion: string,
    history: ConversationMessage[],
    appendUserMessage: boolean,
  ) {
    if (requestInFlight.current) {
      return
    }

    requestInFlight.current = true
    if (appendUserMessage) {
      setMessages((current) => [...current, { role: 'user' as const, content: nextQuestion }].slice(-frontendConfig.maxHistoryMessages))
    }
    setQuestion('')
    setValidationError(null)
    setApiError(null)
    setFailedRequest(null)
    setStatus('loading')

    try {
      const result = await sendChatRequest({ question: nextQuestion, history })
      setResponse(result)
      setMessages((current) => [
        ...current,
        {
          role: 'assistant' as const,
          content: result.message
            ? result.recommendations
              ? `${result.recommendations.map((option) => `- ${option.title}`).join('\n')}\n${result.message}`
              : result.message
            : `${result.recommendation?.title}: ${result.recommendation?.rationale}`,
        },
      ].slice(-frontendConfig.maxHistoryMessages))
      setStatus('success')
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'Something went wrong. Please try again.'
      setApiError(message)
      setFailedRequest({ question: nextQuestion, history })
      setStatus('error')
    } finally {
      requestInFlight.current = false
    }
  }

  async function submitQuestion() {
    if (requestInFlight.current) {
      return
    }

    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) {
      setValidationError('Ask a question before opening the catalogue.')
      setApiError(null)
      setStatus('error')
      return
    }
    if (trimmedQuestion.length > frontendConfig.maxQuestionLength) {
      setValidationError(`Questions must be ${frontendConfig.maxQuestionLength.toLocaleString()} characters or fewer.`)
      setApiError(null)
      setStatus('error')
      return
    }

    const history = messages
      .filter((message) => message.role === 'user' || message.role === 'assistant')
      .slice(-(frontendConfig.maxHistoryMessages - 1))
    await executeRequest(trimmedQuestion, history, true)
  }

  async function retry() {
    if (failedRequest) {
      await executeRequest(failedRequest.question, failedRequest.history, false)
    }
  }

  function clearConversation() {
    setMessages([])
    setQuestion('')
    setResponse(null)
    setValidationError(null)
    setApiError(null)
    setFailedRequest(null)
    setStatus('idle')
  }

  return {
    messages,
    question,
    response,
    validationError,
    apiError,
    error,
    isLoading: status === 'loading',
    status,
    setQuestion,
    submitQuestion,
    retry,
    clearConversation,
  }
}