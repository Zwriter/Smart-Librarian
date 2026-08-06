import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import App from '../../App'
import { createChatServer } from './appTestServer'

const chatServer = createChatServer()

beforeAll(() => chatServer.listen())
afterEach(() => chatServer.resetHandlers())
afterAll(() => chatServer.close())

test('keeps a failed user message visible without adding an assistant message', async () => {
  chatServer.use(http.post('http://127.0.0.1:8000/chat', () => (
    HttpResponse.json({ detail: 'The catalogue is unavailable.' }, { status: 503 })
  )))

  const user = userEvent.setup()
  render(<App />)
  await user.type(screen.getByLabelText('Your question'), 'A quiet mystery')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))

  expect(await screen.findByText('A quiet mystery')).toBeVisible()
  expect(screen.getByRole('alert')).toHaveTextContent('The catalogue is unavailable.')
  expect(screen.queryByText('Librarian')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry request' })).toBeVisible()
})

test('retries the failed request without duplicating the user message', async () => {
  let requestCount = 0
  chatServer.use(http.post('http://127.0.0.1:8000/chat', () => {
    requestCount += 1
    if (requestCount === 1) {
      return HttpResponse.json({ detail: 'Try again.' }, { status: 503 })
    }
    return HttpResponse.json({
      recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'A match.' },
      summary: 'A summary.',
    })
  }))

  const user = userEvent.setup()
  render(<App />)
  await user.type(screen.getByLabelText('Your question'), 'A quiet mystery')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))
  await user.click(await screen.findByRole('button', { name: 'Retry request' }))

  expect(await screen.findByRole('heading', { name: 'Dune' })).toBeVisible()
  expect(screen.getAllByText('A quiet mystery')).toHaveLength(1)
  expect(requestCount).toBe(2)
})

test('prevents duplicate submissions while a request is pending', async () => {
  let releaseResponse!: () => void
  const responseReleased = new Promise<void>((resolve) => {
    releaseResponse = resolve
  })
  let requestCount = 0
  chatServer.use(http.post('http://127.0.0.1:8000/chat', async () => {
    requestCount += 1
    await responseReleased
    return HttpResponse.json({
      recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'A match.' },
      summary: 'A summary.',
    })
  }))

  const user = userEvent.setup()
  render(<App />)
  await user.type(screen.getByLabelText('Your question'), 'A quiet mystery')
  const submitButton = screen.getByRole('button', { name: /ask librarian/i })
  await user.click(submitButton)
  await user.click(screen.getByRole('button', { name: /searching/i }))

  expect(requestCount).toBe(1)
  expect(screen.getAllByText('A quiet mystery')).toHaveLength(1)
  releaseResponse()
  expect(await screen.findByRole('heading', { name: 'Dune' })).toBeVisible()
})

test('clears the conversation and recommendation', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.type(screen.getByLabelText('Your question'), 'A quiet mystery')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))
  expect(await screen.findByRole('heading', { name: 'Dune' })).toBeVisible()

  await user.click(screen.getByRole('button', { name: 'Clear shelf' }))

  expect(screen.getByRole('complementary')).toHaveTextContent('Your recommendation will appear here')
  expect(screen.queryByText('A quiet mystery')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Your question')).toHaveValue('')
})
