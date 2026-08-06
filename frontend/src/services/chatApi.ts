import type { ChatRequest, ChatResponse } from '../types/chat'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

type ErrorPayload = { detail?: unknown }

const FALLBACK_ERROR_MESSAGE = 'The librarian could not answer right now. Please try again.'
const NETWORK_ERROR_MESSAGE = 'The librarian is unavailable. Check that the backend is running.'

function getBackendErrorMessage(payload: unknown): string | undefined {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) {
    return undefined
  }

  const detail = (payload as ErrorPayload).detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => {
      if (typeof item === 'string') {
        return item.trim() ? [item] : []
      }
      if (item && typeof item === 'object' && 'msg' in item) {
        const message = (item as { msg?: unknown }).msg
        return typeof message === 'string' && message.trim() ? [message] : []
      }
      return []
    })
    return messages.length > 0 ? messages.join(' ') : undefined
  }

  return undefined
}

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
    throw new ChatApiError(NETWORK_ERROR_MESSAGE)
  }

  if (!response.ok) {
    let message = FALLBACK_ERROR_MESSAGE
    try {
      message = getBackendErrorMessage(await response.json()) ?? message
    } catch {
      message = FALLBACK_ERROR_MESSAGE
    }
    throw new ChatApiError(message, response.status)
  }

  return (await response.json()) as ChatResponse
}