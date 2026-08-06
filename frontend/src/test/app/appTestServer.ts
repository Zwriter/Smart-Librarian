import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

export function createChatServer() {
  return setupServer(
    http.post('http://127.0.0.1:8000/chat', () => HttpResponse.json({
      recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'Its politics and world-building fit.' },
      summary: 'A complete local summary.',
    })),
  )
}
