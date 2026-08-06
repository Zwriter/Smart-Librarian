import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import App from '../../App'
import { createChatServer } from './appTestServer'

const chatServer = createChatServer()

beforeAll(() => chatServer.listen())
afterEach(() => chatServer.resetHandlers())
afterAll(() => chatServer.close())

test('shows feedback and skips the API for a whitespace-only question', async () => {
  let requestCount = 0
  chatServer.use(http.post('http://127.0.0.1:8000/chat', () => {
    requestCount += 1
    return HttpResponse.json({})
  }))

  const user = userEvent.setup()
  render(<App />)

  await user.type(screen.getByLabelText('Your question'), ' ')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))

  expect(screen.getByRole('alert')).toHaveTextContent('Ask a question')
  expect(requestCount).toBe(0)
})

test('rejects questions over 2,000 characters without sending them', async () => {
  let requestCount = 0
  chatServer.use(http.post('http://127.0.0.1:8000/chat', () => {
    requestCount += 1
    return HttpResponse.json({})
  }))

  render(<App />)
  const questionInput = screen.getByLabelText('Your question')
  fireEvent.change(questionInput, { target: { value: 'x'.repeat(2_001) } })
  await userEvent.setup().click(screen.getByRole('button', { name: /ask librarian/i }))

  expect(screen.getByRole('alert')).toHaveTextContent('2,000 characters or fewer')
  expect(questionInput).toHaveAttribute('aria-invalid', 'true')
  expect(questionInput).toHaveAttribute('aria-describedby', 'question-error')
  expect(requestCount).toBe(0)
})

test('disables submission when the question is empty', () => {
  render(<App />)

  expect(screen.getByRole('button', { name: /ask librarian/i })).toBeDisabled()
})
