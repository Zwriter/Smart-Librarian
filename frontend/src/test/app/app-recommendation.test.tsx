import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import App from '../../App'
import { createChatServer } from './appTestServer'

const chatServer = createChatServer()

beforeAll(() => chatServer.listen())
afterEach(() => chatServer.resetHandlers())
afterAll(() => chatServer.close())

it('submits a question and renders the recommendation and summary', async () => {
  const user = userEvent.setup()
  render(<App />)

  await user.type(screen.getByLabelText('Your question'), 'A science-fiction novel about politics')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))

  expect(await screen.findByRole('heading', { name: 'Dune' })).toBeVisible()
  expect(screen.getByText('Frank Herbert')).toBeVisible()
  expect(screen.getByText('A complete local summary.')).toBeVisible()
})

it('trims whitespace before sending a question', async () => {
  let requestBody: unknown
  chatServer.use(http.post('http://127.0.0.1:8000/chat', async ({ request }) => {
    requestBody = await request.json()
    return HttpResponse.json({
      recommendation: { title: 'Dune', author: 'Frank Herbert', rationale: 'A match.' },
      summary: 'A summary.',
    })
  }))

  const user = userEvent.setup()
  render(<App />)

  await user.type(screen.getByLabelText('Your question'), '  A short question  ')
  await user.click(screen.getByRole('button', { name: /ask librarian/i }))

  expect(await screen.findByRole('heading', { name: 'Dune' })).toBeVisible()
  expect(requestBody).toEqual({ question: 'A short question', history: [] })
})
