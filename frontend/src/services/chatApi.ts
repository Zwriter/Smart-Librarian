import type { ChatRequest, ChatResponse } from '../types/chat'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

type ErrorPayload = { detail?: string }

export class ChatApiError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.status = status
    this.name = 'ChatApiError'
  }
}

export async function sendChatRequest(request: ChatRequest): Promise<ChatResponse> {
  let response: Response

  try {
    response = await fetch(`${apiBaseUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
  } catch {
    throw new ChatApiError('The librarian is unavailable. Check that the backend is running.')
  }

  if (!response.ok) {
    let message = 'The librarian could not answer right now. Please try again.'
    try {
      const payload = (await response.json()) as ErrorPayload
      if (typeof payload.detail === 'string' && payload.detail.trim()) {
        message = payload.detail
      }
    } catch {
      // Keep the safe fallback for non-JSON backend errors.
    }
    throw new ChatApiError(message, response.status)
  }

  return (await response.json()) as ChatResponse
}