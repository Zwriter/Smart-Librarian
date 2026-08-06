import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { sendChatRequest } from './chatApi'

const server = setupServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('sendChatRequest', () => {
  it('serializes the question and supported history', async () => {
    let requestBody: unknown
    server.use(http.post('http://127.0.0.1:8000/chat', async ({ request }) => {
      requestBody = await request.json()
      return HttpResponse.json({
        recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'A match.' },
        summary: 'A complete summary.',
      })
    }))

    await sendChatRequest({
      question: 'I want a mystery novel',
      history: [{ role: 'user', content: 'I enjoyed Sherlock Holmes' }],
    })

    expect(requestBody).toEqual({
      question: 'I want a mystery novel',
      history: [{ role: 'user', content: 'I enjoyed Sherlock Holmes' }],
    })
  })

  it('exposes backend detail errors without logging request content', async () => {
    server.use(http.post('http://127.0.0.1:8000/chat', () => (
      HttpResponse.json({ detail: 'Question was rejected.' }, { status: 400 })
    )))

    await expect(sendChatRequest({ question: 'Noir', history: [] }))
      .rejects.toMatchObject({ message: 'Question was rejected.', status: 400 })
  })
})