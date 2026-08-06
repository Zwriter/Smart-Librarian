import { useState } from 'react'
import { sendChatRequest } from '../services/chatApi'
import type { ChatResponse, ConversationMessage } from '../types/api'
import type { ErrorState, RequestStatus } from '../types/ui'

const MAX_HISTORY_MESSAGES = 20
const MAX_QUESTION_LENGTH = 2_000

export function useChat() {
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<ChatResponse | null>(null)
  const [error, setError] = useState<ErrorState['error']>(null)
  const [status, setStatus] = useState<RequestStatus>('idle')

  async function submitQuestion() {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) {
      setError('Ask a question before opening the catalogue.')
      return
    }
    if (trimmedQuestion.length > MAX_QUESTION_LENGTH) {
      setError('Questions must be 2,000 characters or fewer.')
      return
    }

    const history = messages.slice(-(MAX_HISTORY_MESSAGES - 1))
    const userMessage: ConversationMessage = { role: 'user', content: trimmedQuestion }
    setMessages((current) => [...current, userMessage].slice(-MAX_HISTORY_MESSAGES))
    setQuestion('')
    setError(null)
    setStatus('loading')

    try {
      const result = await sendChatRequest({ question: trimmedQuestion, history })
      setResponse(result)
      setMessages((current) => [
        ...current,
        { role: 'assistant' as const, content: result.recommendation.rationale },
      ].slice(-MAX_HISTORY_MESSAGES))
      setStatus('success')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong. Please try again.')
      setStatus('error')
    }
  }

  function clearConversation() {
    setMessages([])
    setQuestion('')
    setResponse(null)
    setError(null)
    setStatus('idle')
  }

  return {
    messages,
    question,
    response,
    error,
    isLoading: status === 'loading',
    status,
    setQuestion,
    submitQuestion,
    clearConversation,
  }
}