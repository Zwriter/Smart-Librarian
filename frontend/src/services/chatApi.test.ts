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

  it('serializes both user and assistant history roles', async () => {
    let requestBody: unknown
    server.use(http.post('http://127.0.0.1:8000/chat', async ({ request }) => {
      requestBody = await request.json()
      return HttpResponse.json({
        recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'A match.' },
        summary: 'A complete summary.',
      })
    }))

    await sendChatRequest({
      question: 'Something more hopeful',
      history: [
        { role: 'user', content: 'I liked the mystery.' },
        { role: 'assistant', content: 'Try a quieter investigation.' },
      ],
    })

    expect(requestBody).toEqual({
      question: 'Something more hopeful',
      history: [
        { role: 'user', content: 'I liked the mystery.' },
        { role: 'assistant', content: 'Try a quieter investigation.' },
      ],
    })
  })

  it('parses a successful recommendation response', async () => {
    const response = {
      recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'A match.' },
      summary: 'A complete summary.',
    }
    server.use(http.post('http://127.0.0.1:8000/chat', () => HttpResponse.json(response)))

    await expect(sendChatRequest({ question: 'Noir', history: [] })).resolves.toEqual(response)
  })

  it('exposes backend detail errors without logging request content', async () => {
    server.use(http.post('http://127.0.0.1:8000/chat', () => (
      HttpResponse.json({ detail: 'Question was rejected.' }, { status: 400 })
    )))

    await expect(sendChatRequest({ question: 'Noir', history: [] }))
      .rejects.toMatchObject({ message: 'Question was rejected.', status: 400 })
  })

  it('joins validation details from the backend', async () => {
    server.use(http.post('http://127.0.0.1:8000/chat', () => (
      HttpResponse.json({ detail: [{ msg: 'Question is required.' }, { msg: 'History is invalid.' }] }, { status: 422 })
    )))

    await expect(sendChatRequest({ question: '', history: [] }))
      .rejects.toMatchObject({ message: 'Question is required. History is invalid.', status: 422 })
  })

  it('uses a fallback for non-JSON backend errors', async () => {
    server.use(http.post('http://127.0.0.1:8000/chat', () => (
      new HttpResponse('Service unavailable', { status: 503 })
    )))

    await expect(sendChatRequest({ question: 'Noir', history: [] }))
      .rejects.toMatchObject({
        message: 'The librarian could not answer right now. Please try again.',
        status: 503,
      })
  })

  it('reports network failures without exposing request content', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Network error'))

    await expect(sendChatRequest({ question: 'Private question', history: [] }))
      .rejects.toMatchObject({
        message: 'The librarian is unavailable. Check that the backend is running.',
      })

    expect(fetchSpy).toHaveBeenCalledOnce()
    fetchSpy.mockRestore()
  })
})