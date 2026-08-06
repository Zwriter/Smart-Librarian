import { useState } from 'react'
import { sendChatRequest } from '../services/chatApi'
import type { ChatResponse, ConversationMessage } from '../types/chat'

const MAX_HISTORY_MESSAGES = 20
const MAX_QUESTION_LENGTH = 2_000

export function useChat() {
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<ChatResponse | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

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
    setError('')
    setIsLoading(true)

    try {
      const result = await sendChatRequest({ question: trimmedQuestion, history })
      setResponse(result)
      setMessages((current) => [
        ...current,
        { role: 'assistant' as const, content: result.recommendation.rationale },
      ].slice(-MAX_HISTORY_MESSAGES))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  function clearConversation() {
    setMessages([])
    setQuestion('')
    setResponse(null)
    setError('')
  }

  return {
    messages,
    question,
    response,
    error,
    isLoading,
    setQuestion,
    submitQuestion,
    clearConversation,
  }
}